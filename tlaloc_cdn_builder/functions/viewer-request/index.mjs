
import { CognitoIdentityProviderClient, GetUserCommand } from '@aws-sdk/client-cognito-identity-provider';
import { DynamoDBClient, GetItemCommand } from '@aws-sdk/client-dynamodb';
import { marshall, unmarshall } from '@aws-sdk/util-dynamodb';
import { CognitoJwtVerifier } from 'aws-jwt-verify';
import { JwtExpiredError } from 'aws-jwt-verify/error';
import { WeelockErrors } from './errors/WeelockErrors.mjs';
import { parse } from 'path';

const tableConfigAccess = 'maketemplate_table_config_access';
const userPoolClientId = 'maketemplate_user_pool_client_id';
const userPoolId = 'maketemplate_user_pool_id';

const cognitoClient = new CognitoIdentityProviderClient({ region: 'sa-east-1' });
const dynamodbClient = new DynamoDBClient({ region: 'sa-east-1' });
const verifier = CognitoJwtVerifier.create({
    clientId: userPoolClientId,
    includeRawJwtInErrors: true,
    tokenUse: 'access',
    userPoolId,
});

export async function handler(event) {
    let request = null;
    try {
        // Obtaining request
        request = prepareRequest(event);
        // Adding authentication header
        request.headers['weelock-authentication'] = [{
            key: 'Weelock-Authentication',
            value: await authenticate(request),
        }];
        // Send to origin
        return request;
    } catch (exception) {
        if (exception.fastResponse) {
            return request;
        } else if (exception.response) {
            return exception.response;
        }
        throw exception;
    }
}

function prepareRequest(event) {
    const { request } = event.Records[0].cf;
    // Removing potential viewer weelock_authentication header
    if (request.headers['weelock-authentication']) {
        delete request.headers['weelock-authentication'];
    }
    return request;
}

function getCookies(request) {
    const cookiesRetrieved = {};
    if (request.headers && request.headers.cookie) {
        const cookies = request.headers.cookie[0].value.split(';');
        cookies.forEach((cookie) => {
            const parts = cookie.trim().split('=');
            const key = parts[0].trim();
            const value = parts[1].trim();
            cookiesRetrieved[key] = value;
        });
    }
    return cookiesRetrieved;
}

function isUriExempted(uri) {
    const uriParsed = parse(uri);
    // Object is in the root
    if (uriParsed.dir === '/' && uriParsed.ext !== '') {
        return true;
    }
    // Request is for the oauth api
    if (uriParsed.dir === '/api/profile/oauth/token') {
        return true;
    }
    // The object is a common asset
    if (/^\/assets(?:\/|$)/u.test(uriParsed.dir)) {
        return true;
    }
    // The object is an error page
    if (uriParsed.dir === '/errors') {
        return true;
    }
    return false;
}

// eslint-disable-next-line require-await
async function cognitoVerifyAccessToken(accessToken, uri, querystring) {
    const command = new GetUserCommand({ AccessToken: accessToken });
    return cognitoClient.send(command)
        .then((data) => data.UserAttributes)
        .catch((error) => {
            if (error.name !== 'NotAuthorizedException') {
                // eslint-disable-next-line no-console
                console.log('Error validating access token:', error);
            }
            if (isUriExempted(uri)) {
                return {};
            }
            if (uri.startsWith('/api/')) {
                // If trying to reach the API returns a 401 for the front to handle
                return new WeelockErrors.ExpiredAccessToken();
            }
            // Browser trying to access a resource with an expired token, redirect to root front for refreshing an returning
            return new WeelockErrors.Redirect(uri.replace(/^\/index\.html$/u, '/'), 'Expired access-token', querystring);
        });
}

// eslint-disable-next-line require-await
async function userGetConfig(claimSub) {
    const params = {
        Key: marshall({
            sub: claimSub,
        }),
        TableName: tableConfigAccess,
    };
    return dynamodbClient.send(new GetItemCommand(params))
        .then((data) => {
            if (data.Item) {
                const item = unmarshall(data.Item);
                item.valid = true;
                return item;
            }
            return {
                valid: true,
            };
        })
        .catch((error) => {
            // eslint-disable-next-line no-console
            console.log(error);
            return {
                valid: false,
            };
        });
}

// eslint-disable-next-line require-await
async function jwtVerifyAccessToken(accessToken) {
    try {
        const data = await verifier.verify(accessToken);
        return {
            groups: data['cognito:groups'],
            sub: data.sub,
        };
    } catch (error) {
        if (error instanceof JwtExpiredError) {
            return {
                groups: error.rawJwt.payload['cognito:groups'],
                sub: error.rawJwt.payload.sub,
            };
        }
        throw new WeelockErrors.InvalidAccessToken();
    }
}

function initializeAuthentication(request) {
    const cookies = getCookies(request);
    if (cookies['access-token']) {
        return {
            accessToken: cookies['access-token'],
            accessTokenSource: 'COOKIE',
        };
    } else if (request.uri.startsWith('/api/')) {
        if (request.headers && request.headers['access-token']) {
            return {
                accessToken: request.headers['access-token'][0].value,
                accessTokenSource: 'HEADER',
            };
        }
    }
    request.headers['weelock-authentication'] = [{
        key: 'weelock-authentication',
        value: JSON.stringify({
            accessTokenSource: 'NONE',
        }),
    }];
    throw new WeelockErrors.NoAccessToken();
}

async function authenticate(request) {
    const authentication = initializeAuthentication(request);
    authentication.userAttributes = cognitoVerifyAccessToken(authentication.accessToken, request.uri, request.querystring);
    authentication.claims = await jwtVerifyAccessToken(authentication.accessToken);
    authentication.config = await userGetConfig(authentication.claims.sub);
    authentication.userAttributes = await authentication.userAttributes;
    if (authentication.userAttributes instanceof Error) {
        throw authentication.userAttributes;
    }
    authentication.authorized = Object.keys(authentication.userAttributes).length !== 0;
    delete authentication.accessToken;
    return JSON.stringify(authentication);
}
