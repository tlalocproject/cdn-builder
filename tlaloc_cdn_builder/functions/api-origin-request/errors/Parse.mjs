
export class Parse extends Error {
    constructor() {
        super('Parse');
        this.name = 'Parse';
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
                    value: 'OReq: Cannot parse weelock-authentication header',
                }],
            },
            status: '400',
        };
    }
}
