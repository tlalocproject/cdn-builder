
export class NoAccessToken extends Error {
    constructor() {
        super('NoAccessToken');
        this.name = 'NoAccessToken';
        this.fastResponse = true;
    }
}
