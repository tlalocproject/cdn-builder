
export class Forbidden extends Error {
    constructor(method) {
        super('Forbidden');
        this.name = 'Forbidden';
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
                    value: `OReq: The account does not have permissions to call ${method} use this api resource`,
                }],
            },
            status: '403',
        };
    }
}
