
import { DynamoDBClient, QueryCommand } from '@aws-sdk/client-dynamodb';
import { SQSClient, SendMessageCommand } from '@aws-sdk/client-sqs';
import { WeelockErrors } from './errors/WeelockErrors.mjs';
import { minimatch } from 'minimatch';
import { unmarshall } from '@aws-sdk/util-dynamodb';

const awsAccountId = 'maketemplate_aws_account_id';
const makePrefix = 'maketemplate_make_prefix';
const queueSyslogWrite = `https://sqs.sa-east-1.amazonaws.com/${awsAccountId}/${makePrefix}_user_syslogWrite.fifo`;
const tableConfigPermissions = 'maketemplate_table_config_permissions';

const sqsClient = new SQSClient({ region: 'sa-east-1' });

// Default api version for when weelockAuthentication does not have the information
const apiVersionDefault = {
    'api_admin_version': 'V000000',
    'api_profile_version': 'V000000',
    'api_service_version': 'V000000',
    'api_user_version': 'V000000',
};

const dynamoClient = new DynamoDBClient({ region: 'sa-east-1' });

export async function handler(event) {
    let request = null;
    try {
        // Obtaining request
        ({ request } = event.Records[0].cf);
        // Getting weelock authentication header
        const weelockAuthentication = getWeelockAuthentication(request);
        // Getting permissions
        const permissions = (await getPermissions(weelockAuthentication)).filter((permission) => permissionsFilter(permission, request, weelockAuthentication));
        // Checking permissions
        if (permissions.filter((permission) => permission.effect === 'allow').length === 0) {
            if (weelockAuthentication.authorized) {
                throw new WeelockErrors.Forbidden(request.method);
            } else {
                throw new WeelockErrors.NotAuthenticated();
            }
        }
        const conditionalParameters = getConditionalParameters(weelockAuthentication, request);
        checkProhibitions(permissions, conditionalParameters);
        checkAuthorizations(permissions, conditionalParameters);
        // Resolve API endpoint
        resolveApiEndpoint(weelockAuthentication, request);
        // Return
        return request;
    } catch (exception) {
        if (exception.response) {
            event.Records[0].cf.response = exception.response;
            return await syslogWrite(event);
        }
        throw exception;
    }
}

async function syslogWrite(event) {
    const params = {
        MessageBody: JSON.stringify({
            item: event,
            operation: 'api-origin-request',
        }),
        MessageDeduplicationId: String(Date.now()),
        MessageGroupId: 'default',
        QueueUrl: queueSyslogWrite,
    };
    try {
        const command = new SendMessageCommand(params);
        await sqsClient.send(command);
    } catch (exception) {
        // eslint-disable-next-line no-console
        console.log(exception);
    }
    return event.Records[0].cf.response;
}

function resolveApiEndpoint(weelockAuthentication, request) {
    const apiVersionConfig = `api_${request.uri.split('/')[2]}_version`;
    let apiVersion = apiVersionDefault[apiVersionConfig];
    if (weelockAuthentication.config && weelockAuthentication.config.valid) {
        if (weelockAuthentication.config[apiVersionConfig]) {
            apiVersion = weelockAuthentication.config[apiVersionConfig];
        }
    }
    request.uri = `/${request.uri.split('/').slice(3).join('/')}`;
    request.uri = `/${apiVersion}${request.uri}`;
    return true;
}

function checkProhibitions(permissions, conditionalParameters) {
    const permissionsDeny = permissions.filter((permission) => permission.effect === 'deny');
    if (permissionsDeny.filter((permission) => !permission.condition).length > 0) {
        throw new WeelockErrors.Forbidden(conditionalParameters.request.method);
    }
    for (let iter = 0; iter < permissionsDeny.length; iter += 1) {
        const permission = permissionsDeny[iter];
        // eslint-disable-next-line no-new-func
        const conditionValidation = new Function('parameters', permission.condition);
        if (conditionValidation(conditionalParameters)) {
            throw new WeelockErrors.Forbidden(conditionalParameters.request.method);
        }
    }
}
function checkAuthorizations(permissions, conditionalParameters) {
    const permissionsAllow = permissions.filter((permission) => permission.effect === 'allow');
    if (permissionsAllow.filter((permission) => !permission.condition).length > 0) {
        return true;
    }
    for (let iter = 0; iter < permissionsAllow.length; iter += 1) {
        const permission = permissionsAllow[iter];
        // eslint-disable-next-line no-new-func
        const conditionValidation = new Function('parameters', permission.condition);
        if (conditionValidation(conditionalParameters)) {
            return true;
        }
    }
    throw new WeelockErrors.Forbidden(conditionalParameters.request.method);
}

function getConditionalParameters(weelockAuthentication, request) {
    return {
        request,
        weelockAuthentication,
    };
}

function permissionsFilter(permission, request, weelockAuthentication) {
    // Filter method
    if (!permission.methods.has('*') && !permission.methods.has(request.method)) {
        return false;
    }
    // Filter resource
    if (!minimatch(request.uri, permission.resource)) {
        return false;
    }
    // Filter method negation
    if (permission.methods.has(`!${request.method}`)) {
        return false;
    }
    // Check exception
    if (!weelockAuthentication.authorized && !permission.authorized_exception) {
        return false;
    }
    return true;
}

async function getPermissions(weelockAuthentication) {
    const permissions = [].concat(await Promise.all([
        getPermissionsUser(weelockAuthentication),
        getPermissionsGroup(weelockAuthentication),
    ]));
    return permissions.flat();
}

async function getPermissionsUser(weelockAuthentication) {
    const queries = [];
    const queryDefault = {
        ExpressionAttributeNames: {
            '#sub': 'sub',
        },
        ExpressionAttributeValues: {
            ':sub': { 'S': '*' },
        },
        IndexName: 'sub-index',
        KeyConditionExpression: '#sub = :sub',
        TableName: tableConfigPermissions,
    };
    queries.push(dynamoClient.send(new QueryCommand(queryDefault)));
    if (weelockAuthentication.claims && weelockAuthentication.claims.sub) {
        const querySpecific = {
            ExpressionAttributeNames: {
                '#sub': 'sub',
            },
            ExpressionAttributeValues: {
                ':sub': { 'S': weelockAuthentication.claims.sub },
            },
            IndexName: 'sub-index',
            KeyConditionExpression: '#sub = :sub',
            TableName: tableConfigPermissions,
        };
        queries.push(dynamoClient.send(new QueryCommand(querySpecific)));
    }
    return (await Promise.all(queries)).flatMap((queryItem) => queryItem.Items.flatMap((queryItemItem) => unmarshall(queryItemItem)));
}

async function getPermissionsGroup(weelockAuthentication) {
    const queries = [];
    if (weelockAuthentication.claims && weelockAuthentication.claims.groups) {
        weelockAuthentication.claims.groups.forEach((group) => {
            const querySpeficic = {
                ExpressionAttributeNames: {
                    '#group': 'group',
                },
                ExpressionAttributeValues: {
                    ':group': { 'S': group },
                },
                IndexName: 'group-index',
                KeyConditionExpression: '#group = :group',
                TableName: tableConfigPermissions,
            };
            queries.push(dynamoClient.send(new QueryCommand(querySpeficic)));
        });
    }
    return (await Promise.all(queries)).flatMap((queryItem) => queryItem.Items.flatMap((queryItemItem) => unmarshall(queryItemItem)));
}

function getWeelockAuthentication(request) {
    if (!request.headers['weelock-authentication']) {
        throw new WeelockErrors.NoWeelockAuthentication();
    }
    try {
        return JSON.parse(request.headers['weelock-authentication'][0].value);
    } catch (error) {
        throw new WeelockErrors.Parse();
    }
}
