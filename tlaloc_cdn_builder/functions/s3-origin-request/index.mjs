
import { WeelockErrors } from './errors/WeelockErrors.mjs';
import { parse } from 'path';

// Default front build for when weelockAuthentication does not have the information
const frontBuildDefault = 'B000000';

export async function handler(event) {
    let request = null;
    try {
        // Obtaining request
        ({request} = event.Records[0].cf);
        // Getting weelock authentication header
        const weelockAuthentication = getWeelockAuthentication(request);
        // Checking authorizations
        request.uri = checkAuthorization(weelockAuthentication, request);
        // Resolving build version
        request.uri = resolveBuildVersion(weelockAuthentication, request);
        // Send to origin
        return request;
    } catch (exception) {
        if (exception.fastResponse) {
            return request;
        } else if (exception.response) {
            return exception.response;
        }
        throw exception;
    }
}

function resolveUri(uri) {
    const uriSplitted = uri.split('/');
    if (!uriSplitted[uriSplitted.length - 1].includes('.')) {
        if (uriSplitted[uriSplitted.length - 1] === '') {
            uriSplitted.pop();
        }
        uriSplitted.push('index.html');
    }
    uriSplitted.splice(2, uriSplitted.length - 3);
    return uriSplitted.join('/');
}

function isUriAuthorizationExempted(uri) {
    const uriParsed = parse(uri);
    if (uriParsed.dir === '/' || /^\/assets(?:\/|$)/u.test(uriParsed.dir) || uriParsed.dir === '/errors') {
        return true;
    }
    return false;

}

function isUriAuthorizedPublic(uri) {
    const uriParsed = parse(uri);
    if (uriParsed.dir === '/' || /^\/assets(?:\/|$)/u.test(uriParsed.dir) || uriParsed.dir === '/profile' || uriParsed.dir === '/errors') {
        return true;
    }
    return false;

}

function isUriFccesibleForMembership(uri, groups) {
    if (!groups || groups.length === 0) {
        return false;
    }
    const entrypointGroups = {
        '/admin': [
            'admin000',
        ],
        '/service': [
            'service000',
        ],
        '/user': [
            'user001',
        ],
    };
    return entrypointGroups[parse(uri).dir].some((element) => groups.includes(element));
}

function getWeelockAuthentication(request) {
    if (!request.headers['weelock-authentication']) {
        throw new WeelockErrors.NoWeelockAuthentication();
    }
    try {
        return JSON.parse(request.headers['weelock-authentication'][0].value);
    } catch (error) {
        throw new WeelockErrors.ParseError();
    }
}

function checkAuthorization(weelockAuthentication, request) {
    const fastResponse = { fastResponse: true };
    const uriResolved = resolveUri(request.uri);
    if (weelockAuthentication.authorized) {
        if (isUriAuthorizedPublic(uriResolved)) {
            if (uriResolved.startsWith('/errors/')) {
                // Fast response for error responses
                throw fastResponse;
            }
        } else if (isUriFccesibleForMembership(uriResolved, weelockAuthentication.claims.groups)) {
            // The uri is accesible at least one of the groups that the user is part off
        } else {
            // Trying to access an object that is not authorized for the user groups
            throw new WeelockErrors.WrongEntryPoint();
        }
    } else if (isUriAuthorizationExempted(uriResolved)) {
        // Accessing public object
        if (uriResolved.startsWith('/errors/')) {
            // Fast track for error responses
            throw fastResponse;
        }
    } else {
        // Trying to access a non public object without authorization
        throw new WeelockErrors.MissingOrExpiredAccessToken();
    }
    return uriResolved;
}

function resolveBuildVersion(weelockAuthentication, request) {
    let frontBuild = frontBuildDefault;
    if (weelockAuthentication.config && weelockAuthentication.config.valid) {
        if (weelockAuthentication.config.front_build) {
            frontBuild = weelockAuthentication.config.front_build;
        }
    }
    return `/${frontBuild}${request.uri}`;
}
