# Common Viewer Request

This function is intended to be used as a lambda@edge function at viewer-request. It will add a stringified json header named **weelock_authorization** to the request received from the viewer before sending it to the origin.

## weelock_authorization format

### Example header when the user is logged in
```json
{
    "accessTokenSource": "COOKIE",
    "authorized": true,
    "claims": {
        "groups": [
            "somegroup"
        ],
        "sub": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    },
    "config": {
        "valid": true
    },
    "user_attributes": [
        {
            "Name": "sub",
            "sub": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        },
        {
            "Name": "email_verified",
            "Value": "true"
        },
        {
            "Name": "email",
            "Value": "name@domain.tld"
        }
    ]
}
```

Notes
- **user_attributes** will include all the attributes stored in cognito

### Example header when the token is valid but expired
```json
{
    "accessTokenSource": "COOKIE",
    "authorized": false,
    "claims": {
        "groups": [
            "somegroup"
        ],
        "sub": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    },
    "config": {
        "valid": true
    },
    "userAttributes": {}
}
```
Notes
- **user_attributes** will be empty because this information is only available if the accessToken is valid
---

&copy; Weelock SpA. All rights reserved.
