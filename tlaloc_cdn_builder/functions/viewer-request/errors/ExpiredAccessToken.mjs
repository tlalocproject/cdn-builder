
export class ExpiredAccessToken extends Error {
    constructor() {
        super('ExpiredAccessToken');
        this.name = 'ExpiredAccessToken';
        this.response = {
            headers: {
                //// IF type branch
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
                    value: 'VReq: Expired access-token',
                }],
            },
            status: '401',
        };
    }
}
