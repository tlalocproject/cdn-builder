
import { SQSClient, SendMessageCommand } from '@aws-sdk/client-sqs';

const awsAccountId = 'maketemplate_aws_account_id';
const makePrefix = 'maketemplate_make_prefix';
const queueSyslogWrite = `https://sqs.sa-east-1.amazonaws.com/${awsAccountId}/${makePrefix}_user_syslogWrite.fifo`;

const sqsClient = new SQSClient({ region: 'sa-east-1' });

export async function handler(event) {
    const { response } = event.Records[0].cf;
    //// IF make_type per
    if (!response.headers['access-control-allow-headers']) {
        response.headers['Access-Control-Allow-Headers'] = [{
            key: 'Access-Control-Allow-Headers',
            value: '*',
        }];
    }
    if (!response.headers['access-control-allow-methods']) {
        response.headers['Access-Control-Allow-Methods'] = [{
            key: 'Access-Control-Allow-Methods',
            value: '*',
        }];
    }
    if (!response.headers['access-control-allow-origin']) {
        response.headers['Access-Control-Allow-Origin'] = [{
            key: 'Access-Control-Allow-Origin',
            value: '*',
        }];
    }
    //// ENDIF
    if (!response.headers.message && parseInt(response.status, 10) >= 400) {
        response.headers.message = [{
            key: 'message',
            value: `API: ${response.statusDescription}`,
        }];
        response.body = '';
    }
    return await syslogWrite(event);
}

async function syslogWrite(event) {
    const params = {
        MessageBody: JSON.stringify({
            item: event,
            operation: 'api-origin-response',
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
