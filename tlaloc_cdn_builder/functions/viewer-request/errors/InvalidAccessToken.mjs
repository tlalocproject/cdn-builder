
export class InvalidAccessToken extends Error {
    constructor() {
        super('InvalidAccessToken');
        this.name = 'InvalidAccessToken';
        this.response = {
            headers: {
                //// IF make_type per
                'Access-Control-Allow-Headers': [{
                    key: 'Access-Control-Allow-Headers',
                    value: '*',
                }],
                'Access-Control-Allow-Methods': [{
                    key: 'Access-Control-Allow-Methods',
                    value: '*',
                }],
                'Access-Control-Allow-Origin': [{
                    key: 'Access-Control-Allow-Origin',
                    value: '*',
                }],
                //// ENDIF
                'message': [{
                    key: 'Message',
                    value: 'VReq: Invalid access-token',
                }],
                'set-cookie': [{
                    key: 'Set-Cookie',
                    value: 'access-token=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT',
                }],
            },
            status: '401',
        };
    }
}
