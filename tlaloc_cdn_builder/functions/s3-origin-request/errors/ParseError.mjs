
export class ParseError extends Error {
    constructor() {
        super('ParseError');
        this.name = 'ParseError';
        this.response = {
            headers: {
                'message': [{
                    key: 'Message',
                    value: 'Oreq: Cannot parse weelock-authentication header',
                }],
            },
            status: '400',
        };
    }
}
