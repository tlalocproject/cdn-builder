
export class WrongEntryPoint extends Error {
    constructor() {
        super('WrongEntryPoint');
        this.name = 'WrongEntryPoint';
        this.response = {
            headers: {
                'message': [{
                    key: 'Message',
                    value: 'Oreq: User do not belongs to any group authorized to access this path',
                }],
            },
            status: '403',
        };
    }
}
