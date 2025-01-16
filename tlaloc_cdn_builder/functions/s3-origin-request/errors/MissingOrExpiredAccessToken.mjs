
export class MissingOrExpiredAccessToken extends Error {
    constructor() {
        super('MissingOrExpiredAccessToken');
        this.name = 'MissingOrExpiredAccessToken';
        this.response = {
            headers: {
                'message': [{
                    key: 'Message',
                    value: 'Oreq: Missing or expired access-token',
                }],
            },
            status: '401',
        };
    }
}
