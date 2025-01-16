
export class NotAuthenticated extends Error {
    constructor() {
        super('NotAuthenticated');
        this.name = 'NotAuthenticated';
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
                    value: 'OReq: The request credentials do not exists or cannot be validated',
                }],
            },
            status: '401',
        };
    }
}
