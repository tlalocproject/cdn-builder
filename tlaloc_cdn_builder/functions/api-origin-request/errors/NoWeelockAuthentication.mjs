
export class NoWeelockAuthentication extends Error {
    constructor() {
        super('NoWeelockAuthentication');
        this.name = 'NoWeelockAuthentication';
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
                    value: 'OReq: Origin request without weelock-authentication header',
                }],
            },
            status: '401',
        };
    }
}
