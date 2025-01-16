
export class NoWeelockAuthentication extends Error {
    constructor() {
        super('NoWeelockAuthentication');
        this.name = 'NoWeelockAuthentication';
        this.response = {
            headers: {
                'message': [{
                    key: 'Message',
                    value: 'Oreq: No weelock-authentication header',
                }],
            },
            status: '401',
        };
    }
}
