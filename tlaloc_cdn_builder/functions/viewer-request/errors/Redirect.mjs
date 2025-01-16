
export class Redirect extends Error {
    constructor(uri, reason, querystring) {
        super('Redirect');
        this.name = 'Redirect';
        let uriComposed = uri;
        if (querystring) {
            uriComposed = `${uri}?${querystring}`;
        }
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
                'location': [{
                    key: 'Location',
                    value: `/?redirect=${encodeURIComponent(uriComposed)}`,
                }],
                'message': [{
                    key: 'Message',
                    value: `VReq: ${reason}`,
                }],
            },
            status: '302',
        };
    }
}
