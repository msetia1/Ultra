OAuth 2.0 authentication
Linear supports OAuth2 authentication, which is recommended if you’re building applications to integrate with Linear.

It is highly recommended you create a workspace for the purpose of managing the OAuth2 Application, as each admin user will have access.

OAuth2 applications created from October 1, 2025 onwards have refresh tokens enabled by default for user-initiated OAuth with no option to disable them.

Create an OAuth2 application
Create a new OAuth2 Application and configure the redirect callback URLs to your application.

Redirect user access requests to Linear
When authorizing a user to the Linear API, redirect to an authorization URL with correct parameters and scopes:

GET https://linear.app/oauth/authorize HTTP/1.1
Name

Description

client_id

(required) Client ID provided when you create the OAuth2 Application

redirect_uri

(required) Redirect URI

response_type=code

(required) Expected response type

scope

(required) Comma separated list of scopes:

read - (Default) Read access for the user's account. This scope will always be present.
write - Write access for the user's account. If your application only needs to create comments, use a more targeted scope
issues:create - Allows creating new issues and their attachments
comments:create - Allows creating new issue comments
timeSchedule:write - Allows creating and modifying time schedules
admin - Full access to admin level endpoints. You should never ask for this permission unless it's absolutely needed
See App authentication for agent-specific scopes such as app:assignable or app:mentionable.

state

(optional) Prevents CSRF attacks and should always be supplied. Read more about it here

prompt=consent

(optional) The consent screen is displayed every time, even if all scopes were previously granted. This can be useful if you want to give users the opportunity to connect multiple workspaces.

actor

Define how the OAuth application should create issues, comments and other changes:

user - (Default) Resources are created as the user who authorized the application. This option should be used if you want each user to do their own authentication
app - Resources are created as the application. This option should be used for agents and service accounts or agents.
PKCE
Linear supports the PKCE flow. To use this flow, you'll need to include two additional parameters as part of your /authorize request:

Name

Description

code_challenge

(required) Code challenge you generated

code_challenge_method

(required) Either plain or S256, depending on whether the challenge is the plain verifier string or the SHA256 hash of the string

Example
GET https://linear.app/oauth/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URL&state=SECURE_RANDOM&scope=read HTTP/1.1
 
GET https://linear.app/oauth/authorize?client_id=client1&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Foauth%2Fcallback&response_type=code&scope=read,write HTTP/1.1
 
GET https://linear.app/oauth/authorize?client_id=client1&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Foauth%2Fcallback&response_type=code&scope=read,write&code_challenge=challenge&code_challenge_method=S256 HTTP/1.1
Handle the redirect URLs you specified in the OAuth2 Application
Once the user approves your application they will be redirected back to your application, with the OAuth authorization code in the URL params.

Any state parameter you specified in step 2 will also be returned in the URL params and must match the value specified in step 2. If the values do not match, the request should not be trusted.

Example
GET https://example.com/oauth/callback?code=9a5190f637d8b1ad0ca92ab3ec4c0d033ad6c862&state=b1ad0ca92 HTTP/1.1
Exchange code for an access token
After receiving the code, you can exchange it for a Linear API access token:

POST https://api.linear.app/oauth/token HTTP/1.1
Pass parameters in body as URL-encoded form submission, where the Content-Type header must be application/x-www-form-urlencoded.

Parameter

Description

code

(required) Authorization code from the previous step

redirect_uri

(required) Same redirect URI which you used in the previous step

client_id

(required) Application's client ID

client_secret

(required) Application's client secret

grant_type=authorization_code

(required)

PKCE
If you are using the PKCE flow, the parameters required by the /token endpoint are different:

Name

Description

code

(required) Authorization code from the previous step

redirect_uri

(required) Same redirect URI which you used in the previous step

client_id


(required) Application's client ID

client_secret

(optional) Application's client secret

code_verifier

(required) The code verifier for the PKCE request that you originally generated before the authorization request

grant_type=authorization_code

(required)

Response
After a successful request, a valid access token will be returned in the response.

If your application has refresh tokens enabled (default behavior for applications created from October 1, 2025 onwards), your response will contain a refresh token along with an access token. The access token is valid for 24 hours and will need to be refreshed when it expires. Example response:

{  
  "access_token": "00a21d8b0c4e2375114e49c067dfb81eb0d2076f48354714cd5df984d87b67cc",
  "token_type": "Bearer",  
  "expires_in": 86399,  
  "scope": "read write",
  "refresh_token": "sz0c8ffy95zj2ff6bh1hiausauw3dbfsu4gly1z4p49b5odqv8l7owunb654vg1f",
}
If your application does not have refresh tokens enabled, your response will contain an access token that is valid for 10 years. Example response:

{
  "access_token": "00a21d8b0c4e2375114e49c067dfb81eb0d2076f48354714cd5df984d87b67cc",
  "token_type": "Bearer",
  "expires_in": 315705599,
  "scope": "read write"
}
Note: OAuth apps created prior to Dec 1, 2023 will instead return scope as an array of strings in the token response.

Refresh an access token
If your application uses refresh tokens, you'll need to use the refresh token you receive alongside your access token to retrieve a new access token when the previous one expires.

For authorization, you have two options:

Use HTTP basic authentication by passing a Base64-encoded client_id:client_secret string as an authorization header: Authorization: Basic <base64(client_id:client_secret)>
Pass client_id and client_secret as parameters
POST https://api.linear.app/oauth/token HTTP/1.1
Pass parameters in body as URL-encoded form submission, where the Content-Type header must be application/x-www-form-urlencoded.

Parameter

Description

refresh_token

(required) Refresh token from the previous step

grant_type=refresh_token

(required)

client_id

(optional, based on authorization method) Application's client ID

client_secret

(optional, based on authorization method) Application's client secret

Response
After a successful request, a new valid access token and a new refresh token will be returned in the response:

{  
  "access_token": "fxra4u0msw3bagb9rdn2i641bs52m9zo8ksoxljouygcu31nh8s2jf8fygbepy16",
  "token_type": "Bearer",  
  "expires_in": 86399,  
  "scope": "read write",
  "refresh_token": "qjmj51q8f8fnwe188702jarfqxwhdy6r5ivqy4yjuhw2crubm5e7nyu84un3marx",
}
Make an API request
Once you have obtained a valid access token, you can make a request to Linear's GraphQL API. You can initialize the Linear Client with the access token:

const client = new LinearClient({ accessToken: response.access_token })
const me = await client.viewer
Or pass the token as an authorization header: Authorization: Bearer <ACCESS_TOKEN>

curl https://api.linear.app/graphql \
  -X POST \
  -H "Content-Type: application/json" \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  --data '{ "query": "{ viewer { id name } }" }' \
Revoke an access token
To revoke a user's access to your application pass the access token as Bearer token in the authorization header (Authorization: Bearer <ACCESS_TOKEN>) or as the access_token form field.

You can also revoke access using a refresh token by passing it as the refresh_token form field.

POST https://api.linear.app/oauth/revoke HTTP/1.1
Response
Expected HTTP status:

200 - token was revoked
400 - unable to revoke token (e.g. token was already revoked)
401 - unable to authenticate with the token
Migrate to using refresh tokens
To ease the transition to refresh tokens for OAuth2 applications that aren't currently using them, we've added a temporary endpoint to migrate any old, long-lived access token to a new, short-lived access token with a refresh token.

POST https://api.linear.app/oauth/migrate_old_token HTTP/1.1
Pass parameters in body as URL-encoded form submission, where the Content-Type header must be application/x-www-form-urlencoded.

Parameter

Description

access_token

(required) Existing long-lived access token

client_id


(required) Application's client ID

client_secret


(required) Application's client secret

Client credentials tokens
We support the client_credentials grant type for OAuth2 apps that use tokens for server-to-server communication and cannot support a user-initiated OAuth flow involving refresh tokens.

You must first toggle on client credentials tokens for your OAuth2 app when creating or editing the app in Linear

The token generated using this grant type will be an app actor token that has access to all public teams in the workspace and is valid for 30 days. You can learn more about app actor tokens here.

The app user's team access can be modified through the app details page for your app at any point after the token is generated. Since there is no refresh token paired with this access token, your server is expected to fetch a new token if it receives a 401 error when making a request with the previous token.

Every OAuth2 app can only have one active client credentials token at a time since it is an app token. If you request a new client credentials token while you still have an active one, we will invalidate the currently active token and return a new token with a 30-day validity.

For increased security, we will also invalidate your app's client credentials token if its client secret is rotated.

Request
For authorization, you have two options:

Use HTTP basic authentication by passing a Base64-encoded client_id:client_secret string as an authorization header: Authorization: Basic <base64(client_id:client_secret)>
Pass client_id and client_secret as parameters
POST https://api.linear.app/oauth/token HTTP/1.1
Name

Description

grant_type=client_credentials

(required)

scope

(required) Comma-separated list of scopes

client_id

(optional, based on authorization method) Application's client ID

client_secret

(optional, based on authorization method) Application's client secret

Response
After a successful request, a new valid access token will be returned in the response:

{  
  "access_token": "fxra4u0msw3bagb9rdn2i621bs52m9zo8ksoxljouygcu31nh8s2jf8fygbepy16",
  "token_type": "Bearer",  
  "expires_in": 2591999,  
  "scope": "read write",
}
If your OAuth2 app does not have client credentials tokens enabled, you will receive an error response:

{
  "error":"Error",
  "error_description":"Client does not support the client_credentials grant type"
}                                              

Getting started
Linear's public API is built using GraphQL. It's the same API we use internally for developing our applications. If you are new to GraphQL, Apollo has resources for beginners. The official GraphQL documentation is another good starting point.

Endpoint
Linear's GraphQL endpoint is:

https://api.linear.app/graphql
It supports introspection so you can query the whole schema.

Authentication
The Linear API supports personal API keys and OAuth2 authentication.

OAuth
If you’re building an application for others to use, we recommend you use OAuth2 authentication. Once you complete the authentication flow and acquire an access token, pass it with the header Authorization: Bearer <ACCESS_TOKEN>

curl \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  --data '{ "query": "{ issues { nodes { id title } } }" }' \
  https://api.linear.app/graphql
Personal API Keys
For personal scripts API keys are the easiest way to access the API. Visit Security & access settings to create and manage them.

To authenticate your requests, you need to pass the API key with header: Authorization: <API_KEY>

curl \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: <Replace this with your API Key>" \
  --data '{ "query": "{ issues { nodes { id title } } }" }' \
  https://api.linear.app/graphql
Error handling
Linear's GraphQL API follows the standard GraphQL error format, returning errors within an errors array in the response. Each error object includes a message describing what went wrong, a path array indicating where in the query the
error occurred, and extensions that may contain additional context such as error codes or validation details.

Always check for the errors array before assuming success—GraphQL queries can partially succeed with a 200 HTTP status, returning some data while
including errors for failed fields. Monitor HTTP status codes for server errors (5xx) and make sure to correctly handle rate limits. Use strongly-typed GraphQL clients when possible to catch validation errors at development time, and always validate required fields to avoid runtime null value errors.

Linear SDK
The Linear SDK exposes the Linear GraphQL schema, and makes it easy to access models, or perform mutations. We recommend using it to interact with the GraphQL API. It is written in TypeScript, allowing all operations to be strongly typed.

Getting Started
We recommend using a GraphQL client to introspect and explore the schema if you are not using the Linear Client (SDK).

Our GraphQL API is explorable and queryable via Apollo Studio, no download or log in required. Click the Schema tab to browse the schema, and click the Explorer tab to run queries.

Once you have your client installed, you can start making queries (read) and mutations (write) to the API.

Queries & Mutations
To get information about the authenticated user, you can use the viewer query:

query Me {
  viewer {
    id
    name
    email
  }
}
As issues (and most other objects) are team based, you first need to get the ID of the team you want to interact with:

query Teams {
  teams {
    nodes {
      id
      name
    }
  }
}
Once you have found the correct team, you can get the issues for that team. Lets make a request with also some other issue metadata:

query Team {
  team(id: "9cfb482a-81e3-4154-b5b9-2c805e70a02d") {
    id
    name
 
    issues {
      nodes {
        id
        title
        description
        assignee {
          id
          name
        }
        createdAt
        archivedAt
      }
    }
  }
}
We can also get an issue by id:

query Issue {
  issue(id: "BLA-123") {
    id
    title
    description
  }
}
Locate the IDs of teams, issues and other entities directly within Linear itself from the command menu: Cmd/Ctrl+K and "Copy model UUID". This will show results based on the page you're currently viewing within Linear.

Creating & Editing Issues
To create a new issue, use a mutation:

mutation IssueCreate {
  issueCreate(
    input: {
      title: "New exception"
      description: "More detailed error report in markdown"
      teamId: "9cfb482a-81e3-4154-b5b9-2c805e70a02d"
    }
  ) {
    success
    issue {
      id
      title
    }
  }
}
This mutation will create a new issue and return its id and title if the call was successful (success: true).

If an issue is created without a specified stateId(the status field for the issue), the issue will be assigned to the team's first state in the Backlog workflow state category. If the "Triage" feature is turned on for the team, then the issue will be assigned to the Triage workflow state.

A common use case after creating an issue is updating the issue. To do this we can use the issueUpdate mutation, using the input field to include whatever it is we want to change. The id provided can be either be the uuid returned by the creation query, or the shorthand id like BLA-123 below.

mutation IssueUpdate {
  issueUpdate(
    id: "BLA-123",
    input: {
      title: "New Issue Title"
      stateId: "NEW-STATE-ID",
    }
  ) {
    success
    issue {
      id
      title
      state {
        id
        name
      }
    }
  }
}
Changes made to an issue's properties in the first 3 minutes are considered part of the issue creation process, and won't be added to the activity log as changes to the issue.

Accessing Images
Linear hosts images and other assets uploaded into Linear behind authentication. Only authenticated users can view their assets. This also applies to the API and all images will require authentication to be displayed outside Linear's application. Regular API authentication (OAuth or API keys) is accepted for displaying images. If you're displaying images outside Linear's applications, you should download and self-host them in your application's environment.

Adding mentions in Markdown
In the Linear application, you can add mentions to users, issues, projects, and other resources by typing @ and then selecting a resource to mention.

In the GraphQL API, mentions can be created in Markdown by using the plain URL of the resource. For example:

https://linear.app/linear/profiles/someuser what do you think about
https://linear.app/linear/issue/LIN-123/some-issue here?
Will convert into:

@user what do you think about @LIN-123 some issue here?

Where the bolded segments are mentions.

Adding collapsible sections in Markdown
For collapsible sections in an issue, comment, or document, use +++ [some section title] to start the section and +++ to end it.

+++ Section title
 
Markdown content (initially hidden)
 
+++
Fetching Updates
If you're working on building an application which displays Linear data and you want the information to update (near) realtime, you have few options. To prevent excessive usage of our API, we recommend that you be mindful about your implementation.

Lets say you're displaying a big number of issues in your application and want to update them:


Do:

Register a programmatic webhook and get updates for all issues for the team. When you detect changes, update the issue information. You can also automatically register webhooks for OAuth applications.
If you have to poll recent changes, order results by returning recently updated issue first. See Pagination section above how to implement this
Filter issues in your GraphQL request instead of fetching all issues and filtering in code.
Don't:

Poll updates for each issue in the application. There should never be a reason to do this and your application might get rate limited. See above tactics to implement this better
If you have any questions, visit the #api channel on our customer Slack.

Other Examples
Queries
There are many ways to fetch issues. One common use case is to get all the issues assigned to a user.

First let's find our user's id:

query {
  users {
    nodes {
      name
      id
    }
  }
}
Now we can use the assignedIssues field on User:

query {
  user(id: "USERID") {
    id
    name
    assignedIssues {
      nodes {
        id
        title
      }
    }
  }
}
We can do the same thing with workflowStates which represent status fields for teams:

query {
  workflowStates {
    nodes {
      id
      name
    }
  }
}
 
query {
  workflowState(id: "WORKFLOW_ID") {
    issues {
      nodes {
        title
      }
    }
  }
}
Archived resources
Archived resources are hidden by default from the paginated responses. They can be included by passing optional includeArchived: true as a query parameter for pagination.

Support
If you run into problems or have questions or suggestions, you can join our customer Slack or send us a note (hello@linear.app). Both options are available through the user menu in the Linear application.
Pagination
All list responses from queries return paginated results. We implement Relay style cursor-based pagination model with first/after and last/before pagination arguments. For example, this is how to query the first 10 issues in your workspace:

query Issues {
  issues(first: 10) {
    edges {
      node {
        id
        title
      }
      cursor
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
To query the next 10, simply pass the value of pageInfo.endCursor as after parameter for the next request. You can do this as long as pageInfo.hasNextPage return true and you'll paginate through all the values in the collection.

The first 50 results are returned by default without query arguments. Pagination also supports simpler syntax where instead of edges you can directly get all the nodes similar to GitHub's GraphQL API:

query Teams {
  teams {
    nodes {
      id
      name
    }
  }
}
By default results are ordered by createdAt field. To get most recently updated resources, you can alternatively order by updatedAt field:

query Issues {
  issues(orderBy: updatedAt) {
    nodes {
      id
      identifier
      title
      createdAt
      updatedAt
    }
  }
}



Filtering
Most results that are paginated can also be filtered. This makes it easy to retrieve specific information, like any issues assigned to a particular user, but much more complex queries are also possible. For example, you could fetch all issues associated with a project that is supposed to be completed next week and have not yet been started.

For example, to return all urgent and high priority issues in the workspace, you can use the following query:

query HighPriorityIssues {
  issues(filter: { 
    priority: { lte: 2 }
  }) {
    nodes {
      id, title, priority
    }
  }
}
The above query will also return any issues that haven’t been given any priority (their priority is 0). To exclude them, you can add another not equals comparator:

query HighPriorityIssues {
  issues(filter: { 
    priority: { lte: 2, neq: 0 }
  }) {
    nodes {
      id, title, priority
    }
  }
}
Comparators
You can use the following comparators on string, numeric, and date fields:

Comparator

Description

eq

Equals the given value

neq

Does not equal the given value

in

Value is in the given collection of values

nin

Value is not in the given collection of values

Numeric and date fields additionally have the following comparators:

Comparator

Description

lt

Less than the given value

lte

Less than or equal to the given value

gt

Greater than then given value

gte

Greater than or equal to the given value

String fields additionally have the following comparators:

Comparator

Description

eqIgnoreCase

Case insensitive eq

neqIgnoreCase

Case insensitive neq

startsWith

Starts with the given value

notStartsWith

Does not start with the given value

endsWith

Ends with the given value

notEndsWith

Does not end with the given value

contains

Contains the given value

notContains

Does not contain the given value

containsIgnoreCase

Case insensitive contains

notContainsIgnoreCase

Case insensitive notContains

Optional values additionally support the null comparator, which can be used to return entities depending on whether the field has a value or not. The following query will return all issues that don't have a description:

query Issues {
  issues(filter: { 
    description: { null: true }
  }) {
    nodes {
      id, title, description
    }
  }
}
Logical operators
By default, all fields described in the filter need to be matched. The filter merges all the conditions together using a logical and operator.

For example, The below example will find all urgent issues that are due in the year 2021.

query Issues {
  issues(filter: { 
    priority: { eq: 1 }
    dueDate: { lte: "2021" }
  }) {
    nodes {
      id, title, priority, dueDate
    }
  }
}
To change the logical operator, all filters support the or keyword that lets you switch to a logical or operator. For example, to filter for low-priority or un-prioritized issues that need to be completed in the year 2021, you can execute the following query:

query Issues {
  issues(filter: { 
    or: [
      { priority: { eq: 4 } },
      { priority: { eq: 0 } }
    ]
    dueDate: { lte: "2021" }
  }) {
    nodes {
      id, title, priority, dueDate
    }
  }
}
Filtering by relationship
Data can also be filtered based on their relations. For example, you can filter issues based on the properties of their assignees. To query all issues assigned to a user with a particular email address, you can execute the following query:

query AssignedIssues {
  issues(filter: { 
    assignee: { email: { eq: "john@linear.app" } }
  }) {
    nodes {
      id
      title
      assignee {
        name
      }
    }
  }
}
Many-to-many relationships can be filtered similarly. The following query will find issues that have the Bug label associated.

query Issues {
  issues(filter: { 
    labels: { name: { eq: "Bug" } }
  }) {
    nodes {
      id, title
    }
  }
}
The above query returns all issues that have at least one label that matches the name Bug. To create a query where all labels on an issue are matched to the filter criteria, you can use the every keyword:

query Issues {
  issues(filter: { 
    labels: { every: { name: { eq: "Bug" } } }
  }) {
    nodes {
      id, title
    }
  }
}
The above would also filter out issues that have multiple labels, regardless of what they are.

Relative time
All date fields support relative time, defined as ISO 8601 durations relative to the current date. This lets you create a filter that always returns all issues that are due in the next 2 weeks, regardless of when you run it:

query IssuesDue {
  issues(filter: { 
    dueDate: { lt: "P2W" }
  }) {
    nodes {
      id, title
    }
  }
}
Examples
Find all bugs and defects from projects that are lead by any user named "John":

query Projects {
  projects(filter: { 
    lead: { name: { startsWith: "John" } } 
  }) {
    nodes {
      issues(filter: { 
        labels: { name: { in: ["Bug", "Defect"] } } 
      }) {
        nodes {
          id
          title
        }
      }
    }
  }
}
Find all issues assigned to me that have a comment containing a thumbs-up emoji:

query Issues {
  viewer {
    assignedIssues(filter: { 
      comments: { body: { contains: "👍" } } 
    }) {
      nodes {
        id
        title
      }
    }
  }
}
Find all issues that have been created by me and have been closed in the past two weeks:

query ClosedIssues {
  viewer {
    createdIssues(filter: { completedAt: { gt: "-P2W" } }) {
      nodes {
        id, title
      }
    }
  }
}
Find all started issues in ongoing projects that don't have an estimate:

query Issues {
  issues(
    filter: {
      estimate: { eq: 0 }
      state: { type: { eq: "started" } }
      project: { state: { eq: "started" } }
    }
  ) {
    nodes {
      title
      estimate
      project {
        name
      }
    }
  }
}


Rate limiting
Calls to our GraphQL API are rate limited to provide equitable access to the API for everyone and to prevent abuse. We are going to be evolving these limits as we gather more information, and encourage your feedback. Any changes to limits will be announced in our Slack community API announcements channel.

We use the leaky bucket algorithm for our rate limiters, which means that your tokens are refilled with a constant rate of LIMIT_AMOUNT / LIMIT_PERIOD.

If you temporarily require higher limits, you can request them by contacting Linear support where we'll review them on a case by case basis.

Avoiding hitting limits
These are best practices for using our APIs that will, in most cases, avoid hitting any rate limits.

Avoid polling
One thing that we especially discourage is polling the API to fetch updates. If you need to know when data updates in Linear, you should use our Webhook functionality.

Avoid fetching unneeded data
Avoid fetching data you don't need by using our filtering functionality. This way you can drill down on specific records only and avoid pagination in some cases.

Keep in mind that by default our pagination returns up to 50 records. When querying for children this can quickly multiply the requested complexity. Consider specifying the amount of records you want returned.

Order data
In certain cases where you do need to fetch all data, we suggest sorting it by the updated timestamp instead of when it was created. This way you can get the most recently changed data first, and avoid paginating through the entire dataset.

Write custom, specific queries
This applies especially if you're using our SDK. If you're fetching lots of different entities or dependencies, or have specific data needs, it's always recommended to write your own custom GraphQL queries and use filters to narrow down the data as much as possible.

API request limits
We limit the amount of requests you make to our GraphQL API. To make it easier to keep track and avoid going over the limits, there are 3 HTTP response headers we send back on each request.

HTTP Header

Description

X-RateLimit-Requests-Limit

The maximum number of API requests you're permitted to make per hour.

X-RateLimit-Requests-Remaining

The number of API requests remaining in the current rate limit window.

X-RateLimit-Requests-Reset

The time at which the current rate limit window resets in UTC epoch milliseconds.

When authenticated using an API key you can make up to 1,500 requests per hour. Requests are associated with the authenticated user, which means all requests by the same user share the same quota even when using different API keys.

When making unauthenticated requests, you are limited to 60 requests per hour. These requests are associated with the originating IP address instead of the user making the request.

Authentication

Limit

per

Period

API key

1,500

User

1 hour

OAuth App

1,200

User (or App User)

1 hour

OAuth App

60

IP Address

1 hour

Query- and mutation- specific request limits
Some queries and mutations have individual request rate limits that are lower than the global request limit. When one of these limits is hit, the Linear API will send the same response as described in Handling rate limited errors. The window for each endpoint can be different, and is described in the response body. We will also send these extra headers:

HTTP Header

Description

X-RateLimit-Endpoint-Requests-Limit

The maximum number of API requests you're permitted to make to this endpoint in a rate limit window.

X-RateLimit-Endpoint-Requests-Remaining

The number of API requests remaining in the current rate limit window.

X-RateLimit-Endpoint-Requests-Reset

The time at which the current rate limit window resets in UTC epoch milliseconds.

X-RateLimit-Endpoint-Name

The name of the endpoint that was rate limited.

Complexity limits
In order to protect our system from queries that are too complex and resource intensive, we calculate the complexity of each query, based on the amount of requested data.

To make it easier to keep track and avoid going over the limits, there are 4 HTTP response headers we send back on each request.

HTTP Header

Description

X-Complexity

The complexity of the query.

X-RateLimit-Complexity-Limit



The maximum number of API complexity points you're permitted to request per hour.

X-RateLimit-Complexity-Remaining

The number of points of API request complexity remaining in the current rate limit window.

X-RateLimit-Complexity-Reset

The time at which the current rate limit window resets in UTC epoch milliseconds.

Requests authenticated using an API key can request up to 250,000 points per hour. Requests are associated with the authenticated user, which means all requests by the same user share the same quota even when using different API keys.

Unauthenticated requests are limited to 10,000 points per hour. These requests are associated with the originating IP address instead of the user making the request.

Authentication

Limit

Per

Period

API key

250,000

User

1 hour

OAuth app

200,000

User (or App User)

1 hour

Unauthenticated

10,000

IP Address

1 hour

Maximum complexity
We also enforce a maximum complexity of a single query at any time to 10,000 points. Your query will always get rejected if it exceeds that.

Understanding query complexity
In order to protect our systems from too complex and resource intensive queries, we calculate the complexity of each query. Each property is 0.1 point, each object is 1 point and any connection multiplies its children's points based on the given pagination argument, or the default 50. The score is then rounded up to the nearest integer.

As an example, let's fetch an object that returns only one user and request only one property. The calculation is 1 + 0.1 = 1.1, which equals a complexity of 2 when rounded up.

query WhoAmI {
  user(id: "me") {
    name
  }
}
Let's now fetch all of our created issue's ID, title and when they were created. This has a complexity of 66. Here's why:

Query

Complexity

user

1 point

createdIssues (assuming 50, the default pagination)

50 points

id, title, createdAt

15 points (50 × 3 × 0.1)

You can use pagination parameters to specify a different limit than the default 50 to let the complexity calculator know how much data you're trying to fetch. This query with an explicit limit of the first 10 nodes then has a complexity of 14.

query MyCreatedIssues {
  user(id: "me") {
    createdIssues(first: 10) {
      nodes {
        id
        title
        createdAt
      }
    }
  }
}
Handling rate limit errors
Once you actually exceed rate limits, Linear API will start returning rate limit error responses. You can catch these by checking the errors in the response body containing the RATELIMITED error code.

{
  "errors": [
    {
      "message": "...",
      "extensions": {
        "code": "RATELIMITED",
        ...
      }
    }
  ]
}


Attachments
Issue attachments allow you to link external resources to issues and display them inside Linear similarly to GitHub Pull Requests. They are designed with API developers in mind and we also use them for upcoming integrations inside Linear.

Example use cases:

Customer support software where an agent can create a Linear issue
Release bot that attached release version to an issue
Unique URLs are a core concept with attachments. They enable building stateless applications and integrations which interact with Linear’s API. Attachment URL is used as an idempotent value if used in conjunction with the same issue id so if you try to re-create an attachment with the same URL on the same issue, the original attachment is updated instead. This enables simple scripts which update the attachment content without storing the attachment ID. You can also query an attachment, and the associated issue, by its URL. This makes creating links to Linear issues from external application easy and again you don't need to track the attachment ID.

It's recommended to create attachments through Linear's OAuth authentication. Then the application icon is used for the attachment by default, but an icon image URL can be specified when creating the attachment that overrides the application icon. For API key auth, you can also provide an icon URL when creating an attachment. The image provided by URL must be of png or jpg format.

Attachments also support key-value metadata. Values can be any string or number and you can store information there related to your integration. Right now metadata is only exposed through the API but we're also considering exposing it in the UI.

Linear's webhooks also support attachments so you can subscribe to get updates for new and updated attachments.

Examples
Create attachment
mutation{
  attachmentCreate(input:{
    issueId: "590a1127-f98b-49fc-ba74-2df8751c089e"
    title: "Exception"
    subtitle: "Open"
    url: "http://exception.com/123"
    iconUrl: "https://exception.com/assets/icon.png"
    metadata: {exceptionId: "exc-123"}
  }){
    success
    attachment{
      id
    }
  }
}
Update attachment
mutation{
  attachmentUpdate(id: "47e14163-404c-4a34-b775-5c536d67760a", input: {
    title: "Exception"
    subtitle: "Resolved"
    metadata: {exceptionId: "exc-123"}
  }){
    success
    attachment{
      id
    }
  }
}
Query attachment
query {
  attachment(id: "47e14163-404c-4a34-b775-5c536d67760a") {
    id
    issue {
      id
      identifier
      title
    }
  }
}
 
query {
  attachmentsForURL(url: "http://exception.com/123") {
    nodes {
      id
      issue {
        id
        identifier
        title
      }
    }
  }
}
Rich metadata
In addition to generic key-value pairs, metadata field can include fields which will be rendered as a rich attachment modal inside Linear. This makes it easier to include data that you would otherwise have to fetch/read by following the attachment link.

Key

Type

Description

title

string

Title for the modal

messages

{ subject?: string, body?: string, timestamp?: string }[]

Messages included in the attachment. Subject, body, and timestamp are all optional, but we suggest always populating body. Keep under 10k characters.

attributes

{ name: string, value: string }[]

Additional attributes which will be rendered in a list.

Formatting
Format

Type

Output example

{variableName__since}

Date as ISO string

"2 days ago", "23 hours ago"

{variableName__relativeTimestamp}

Date as ISO string

If +/- 6 days from current: "today at 9:30 AM", "Friday at 9:30 AM"

If > 6 days from current: "Oct 20, 9:30 AM"

In order to use the date formatting, when creating an attachment provide a date variable (in ISO string format) in the attachment's metadata. You may then add that date with the format {variableName__since} into the attachment subtitle. When the attachment is rendered, we will format the time since that date, or format that date and time relative to current time, depending on which format is being used.

mutation{
  attachmentCreate(input:{
    issueId: "590a1127-f98b-49fc-ba74-2df8751c089e"
    title: "Exception"
    subtitle: "Detected {detectedAt__since}"
    url: "http://exception.com/123"
    iconUrl: "https://exception.com/assets/icon.png"
    metadata: {detectedAt: "2021-07-06T17:10:32.090Z"}
  }){
    success
    attachment{
      id
    }
  }
}
The above query would yield output like the following:



Agent Interaction Guidelines (AIG)
Agents are changing how software is planned, built, reviewed, and deployed. Because agents produce work in abundance, roles and workflows get reshaped. The value shifts to orchestrating input, context engineering, and reviewing output.

This shift demands a new contract for human‑computer interaction. The Agent Interaction Guidelines (AIG) are the foundational, evolving principles and practices for designing agent interactions that integrate more naturally into human workflows.

Principles & practices
An agent should always disclose that it's an agent
When humans and agents work side by side, humans need instant certainty about who they are interacting with. The agent must signal its identity clearly so that it can never be mistaken for a person.

A screenshot of a user dropdown menu listing both agentic and human users. Agents are clearly marked as agents with a small badge.
fig. 01
Clear boundary between human and agentic users
An agent should inhabit the platform natively
By default, agents should be able to work through existing UI patterns and standard actions of the platform they operate in.

A screenshot of an issue activity feed in Linear that shows how an agent changes the issue status and links a GitHub issue.
fig. 02
The agent is able to use the same actions a human user would
An agent should provide instant feedback
Silence leads to uncertainty. When invoked, an agent should provide immediate, but unobtrusive, feedback to reassure the user it has received a request.

A screenshot of a comment thread in Linear. A human user asks the coding agent to take a look at a bug. The agent instantly replies with a "Thinking" indicator.
fig. 03
The agent instantly indicates that it’s processing the request
An agent should be clear and transparent about its internal state
Agents should clearly indicate whether they’re thinking, waiting for input, executing, or finished working. Humans should be able to understand what’s happening at a glance and, when needed, inspect the underlying reasoning, tool calls, prompts, and decision logic.

A screenshot of "Agent Session" showing every step of the agent's thought process
fig. 04
The agent’s reasoning is fully transparent and open to inspection
An agent should respect requests to disengage
When asked to disengage, an agent should step back, immediately – and only re-engage once it’s received a clear signal to do so.

An agent cannot be held accountable
There should be a clear delegation model between humans and agents. An agent can carry out tasks, but the final responsibility should always remain with a human.

A screenshot of an issue that's been delegated to an agent. The UI makes it clear that there is still a human user who is responsible for the issue.
fig. 05
Clear delegation flow between human and agent
Get involved
The Agent Interaction Guidelines are written with the community in mind. If you’re building agents and thinking through these same challenges, join our Slack community to contribute to the conversation.

This page is a living document and we expect to continually add to it as we learn more in practice.



Getting Started
This guide describes how to best integrate an AI agent into Linear. It includes implementation guidelines on how to design an experience that feels native to Linear’s workflows and interaction patterns.

Developer Preview

Linear for Agents APIs are currently in active development and available as a Developer Preview. Functionality and Agent APIs may change before general availability.

Overview
Agents behave similar to other users in a workspace. They can be @mentioned, delegated issues through assignment, create and reply to comments, collaborate on projects and documents, etc. App users are installed and managed by workspace admins.

You can build agents for internal use within your own workspace or for distribution to other organizations. It does not cost anything to develop agents in Linear. To make your agent available to other workspaces, submit your agent to Linear's integration directory.

Additionally, agents installed in your workspace do not count as billable users.

We've created a demo agent built on our Typescript SDK and Cloudflare, if you want to dive straight into an example codebase.

Weather Bot is an agent that will help you look up the weather of any location within a Linear issue.

Setup
Create a new Application and configure the settings as you would for a standard OAuth application.

In the configuration, enable webhooks and make sure to select Agent session events at the bottom. Enabling this category will notify your webhook when events occur that are directly relevant to your app's user.

Note that the name and icon of your application will be how the agent appears in workspaces where it is installed (e.g. in the mention and filter menus), so it is best to choose something short, recognizable, but unique.

If you're just getting started, selecting Inbox notifications and Permission changes may also be helpful. You can read more about these in Interaction Best Practices.

Authentication
Actor and scopes
App authentication is built on top of the standard OAuth2 flow. To install your agent into a Linear workspace in the OAuth authorization url add the actor=app parameter to switch to an app installation rather than requesting authentication as the installing user. Because this will be installed with a workspace scope admin permissions are required to complete the installation.

This new actor type supersedes any references to actor=application and can be used for all agent, app, and service account use-cases.

Mention + assign scopes
To allow for flexibility, the ability to mention and assign your agent is optional and must be requested through the use of two new additional scopes added to the scope query parameter:

Scope	Description
app:assignable	Allow the app to be assigned as a delegate on issues and made a member of projects
app:mentionable	Allow the app to be mentioned in issues, documents, and other editor surfaces
Assigning an issue to your app now sets it as the delegate, not the assignee—so humans maintain ownership while agents act on their behalf.

Customer access scopes
The ability to access customer-related entities in your workspace for your agent must be requested through scopes:

Scope	Description
customer:read	Allow the app to read customer data in the workspace
customer:write	Allow the app to read and write customer data in the workspace
Initiative access scopes
The ability to access initiative-related entities in your workspace for your agent must be requested through scopes:

Scope	Description
initiative:read	Allow the app to read initiative data in the workspace
initiative:write	Allow the app to read and write initiative data in the workspace
Admin
Note that integrations using the actor=app mode are not able to also request admin scope.

Installation
Your app will have a unique ID for each workspace it is installed within, you can find this ID with the following query using the OAuth access token received as part of the installation flow:

query Me {
  viewer {
    id
  }
}
We highly recommend storing this ID alongside your access token so that you can confidently identify your app in different workspaces.

Management
The team access available to your app can be changed or revoked at any time by workspace admins. If you're subscribed to the Permission changes webhook category, a PermissionChange webhook will be sent when access changes occur.

Agent session lifecycle
Once installed and authenticated, your agent is ready to interact in the workspace. The core interaction model centers around the Agent Session, which tracks the lifecycle of a given agent task. Sessions are created automatically when an agent is mentioned or delegated an issue.

Session state is visible to users, and updated automatically based on the agent’s emitted activities. No manual state management is required.

Receiving your first webhook
The most common entry point is delegation—when a user assigns an issue to your agent.

This triggers a created AgentSessionEvent webhook containing an agentSession object with the relevant issue, comment, and context.

To get started, your agent should:

Emit a thought activity within 10 seconds to acknowledge the session has begun
Inspect the issue, comment, previousComments, and guidance fields
Details on the Agent Session webhook structure and how to respond using Agent Activities in Developing the Agent Interaction.



Developing the Agent Interaction
Once your agent is installed and authenticated, it can begin participating in workflows inside Linear. Agents become active participants through the Agent Session and Agent Activity system—primitives that make agent behavior visible, contextual, and collaborative for end users.

The following sections walk through how your agent will receive instructions though webhooks, how it should communicate back through Agent Activities, and how the Agent Session lifecycle helps track it all.

You can use the GraphQL schema explorer to look up the object types used in agent webhook payloads.

Agent session
AgentSession tracks the lifecycle of an agent run. Session states let the user know if the agent is currently working, waiting for user input, in an error state, or has finished work. An AgentSession is created automatically when an agent is mentioned or delegated an issue.

Session states
Agent sessions can have one of 5 states: pending, active, error, awaitingInput, complete. These will be visible to users.

You don’t need to manage agent session state manually. Linear tracks session lifecycle automatically based on the last emitted activity.

Session external URL
You can set an externalUrl on an AgentSession so users can open the current session on your web dashboard.

Use the agentSessionUpdateExternalUrl mutation to set this value. Pass null to remove it.

Agent Session UI showing an Open button that links to the session’s external URL, allowing users to view the session in the agent provider’s dashboard.
Session webhooks
An AgentSession webhook is sent to notify your agent when it's mentioned, delegated an issue through assignment, or when a user provides additional prompts.

To receive these events, enable the agent session events webhooks category in your OAuth application configuration.

You must return a response from your webhook receiver within 5 seconds.

Once you subscribe to AgentSessionEvent webhooks, customers will begin seeing Agent Session UI in Linear. This happens as soon as the event category is enabled, even if you’re only listening for debugging purposes.

If you receive a created event, you are expected to send an activity or update your external URL within 10 seconds to avoid the session being marked as unresponsive.

AgentSessionEvent webhooks only send events to your specific agent.

There will be two types of actions in the AgentSessionEvent category, denoted by the action field of the payload:

Action

Behavior

created

A new Agent Session has been created (triggered by a user mention or delegation). You should start a new agent loop in response. Relevant input may be included in the agentSession.issue, agentSession.comment, previousComments, or guidance. Your agent can use all of this context to determine what action to take.

The guidance field provides agent-specific instructions configured at the workspace, parent team, or team level—such as preferred repositories or task constraints.

Your agent should consider all of this input when deciding how to respond.

prompted

A user sent a new message into an existing Agent Session. You should insert that message into the conversation history and take action. You should mainly pay attention to the agentActivity field’s body, as the user’s input is usually located there.

For a detailed reference of all Agent Session webhook fields, see the AgentSessionEventWebhookPayload schema.

Proactively creating sessions
If your agent was not delegated or mentioned but you would like to proactively create an agent session, you can do so via the SDK or API with the agentSessionCreateOnIssue or agentSessionCreateOnComment mutations.

Agent activity
Agents communicate progress by emitting semantic agent activities to an AgentSession. These activities can represent thoughts, tool calls, prompts for clarification, final responses, or errors.

Sending agent activities
Agents should communicate progress by emitting Agent Activities to Linear. These activities can represent thoughts, actions, prompts for clarification, final responses, or errors.

You can emit activities using either the TypeScript SDK or a direct GraphQL mutation:

TypeScript SDK

const { success, agentActivity } = await linearClient.createAgentActivity({
  agentSessionId: "...",
  content: {
    type: "...", 
    ... // other payload fields - see below
  },
});
GraphQL

# Operation
mutation AgentActivityCreate($input: AgentActivityCreateInput!) {
  agentActivityCreate(input: $input) {
    success
    agentActivity {
      ...
    }
  }
}
 
# Variables
{
	"input": {
		"agentSessionId": "...",
        # Shape of `content` varies by activity `type`
		"content": {
			"type": "...",
			... # other payload fields - see below
		} 
	}
}
To include mentions in Agent Activity content, use plain Linear URLs in Markdown. These will be converted into mentions in the UI. For example:

https://linear.app/linear/profiles/user, I've created a new Linear issue for tracking the documentation work: https://linear.app/linear/issue/LIN-123/docs-issue — please review.

Renders as: "@user, I've created a new Linear issue for tracking the documentation work: @LIN-123 docs issue — please review.".

More on mentions in Adding mentions in Markdown.

Activity content payload
Your agent may emit one of five allowed activity types. These are validated server-side, and invalid shapes will be rejected. Unless otherwise noted, all fields shown are required. Markdown is supported in body fields.

Additionally, you may see references to a prompt type AgentActivity. That is a user-generated message, usually as a follow-up prompt or responding to an elicitation. These are the messages that emit a prompted webhook to you on creation.

An agent cannot generate a prompt type activity.

Signals
Signals are optional metadata that modify how an Agent Activity should be interpreted or handled by the recipient. They provide additional context about the sender’s intent—guiding how the activity should be processed or responded to.

For details on available signals and sample usage, see Signals.

Ephemeral activities
When creating an agent activity, you may optionally mark it as ephemeral. Ephemeral activities are displayed temporarily, and will be replaced when the next activity arrives from the agent. This could be helpful when displaying temporary states.

Only thought or action type activities can be marked ephemeral.

Seek to:00:02 / Duration00:12
Recommendations
For recommendations on improving agent interaction—like managing delegation and status updates—continue to best practices.



Interaction Best Practices
Linear users have high expectations for the quality and consistency of the experience inside Linear. We aim to extend this to agents, which should act in a predictable and natural manner.

Recommendations
Upon receiving the created webhook, your agent should respond immediately with a thought activity to acknowledge that the agent has started working. This lets the user know right away that their prompt has been received.

The first response must be sent within 10 seconds of receiving the created event, or the agent will be shown as unresponsive.

Follow-up activities after the first response can still be sent for up to 30 minutes before the session is considered stale. Note that this stale state is recoverable by sending another agent activity.

If your agent is delegated to work on an issue that is not in a started, completed, or canceled status type, move the issue to the first status in started when your agent begins work.

If your agent is working on implementation and no Issue.delegate is currently set, it should set itself as the delegate to make the agent's role in the issue more explicit.

When work is complete, emit an AgentActivity with type response; or if you require additional actions from the user, emit an AgentActivity with type elicitation or error. We will automatically create a comment under the comment thread as well.

Agent Activities
Comments may not be reliable to read from, as they are editable and may have changed since your agent’s last run. Instead, rely on Agent Activities as these are frozen-in-time snapshots of user input.

To reconstruct the full conversation, list the Agent Activities associated with the Agent Session instead—see below for examples:

Additional Webhooks
In addition to the core AgentSession webhooks, there are additional webhooks that your agent can listen to in order to build a richer agent experience within Linear. In addition, you can utilize any of the existing GraphQL APIs.

Inbox Notifications Webhooks
Inbox Notification events are triggered when something directly involves your app user—like when an agent is unassigned from an issue or a user reacts to a comment from the agent.

Enable this category by selecting Inbox Notifications in your OAuth app config.

The received webhook payload will have the following shape:

{
  type: "AppUserNotification",
  action: NotificationType,
  createdAt: string,
  organizationId: string,
  oauthClientId: string,
  appUserId: string,
  notification: Notification,
}
Here are a few action types that could be useful while developing your agent:

issueMention
issueEmojiReaction
issueCommentMention
issueCommentReaction
issueAssignedToYou
issueUnassignedFromYou
issueNewComment
issueStatusChanged
Permission Change Webhooks
Permission Change events are triggered when your agent gains or loses access to a team.

Enable this category by selecting Permission changes in your OAuth app config. The webhook will be of type PermissionChange with action teamAccessChanged.

The received webhook payload will have the following shape when team access is granted or removed:

{
  type: "PermissionChange",
  action: "teamAccessChanged",
  createdAt: string,
  organizationId: string,
  oauthClientId: string,
  appUserId: string,
  canAccessAllPublicTeams: boolean,
  addedTeamIds: string[],
  removedTeamIds: string[],
  webhookTimestamp: number,
  webhookId: string
}
 
You’ll receive a separate webhook when revoking your OAuth app:

{
  type: "OAuthApp",
  action: "revoked",
  createdAt: string,
  organizationId: string,
  oauthClientId: string,
  webhookTimestamp: number,
  webhookId: string
}
 
Existing integrations
When to build an integration or agent
If your integration primarily reads data from Linear or performs actions that should be attributed to individual team members, an integration is the right choice.

Build an agent if you want your application to appear as a distinct workspace member with its own identity and actions within Linear.

Convert an existing integration
If you have an existing Linear integration it can be converted to use the new authentication and gain the new functionality.

The new actor=app actor type works quite differently at the core to our legacy actor=application approach. However, if you are using actor=application today to request a token that is only used to create issues or comments as an app, then it is backwards compatible – you can simply change this parameter.

actor=application allows for dual-purpose authentication tokens that can be used both as the authenticating user in some circumstances and as an "app" in others. If you currently are using a token like this, then to migrate you will need to ask users to authenticate twice: once for their personal access and secondarily for the app installation.

Feedback, requests, questions
Please join the #api-agents channel in our community Slack to provide feedback on this guide, request API's, and interact with other engineers developing agentic integrations.



Signals
Signals are optional metadata that modify how an Agent Activity should be interpreted or handled by the recipient. They provide additional context about the sender’s intent—guiding how the activity should be processed or responded to.

Both agents and human users can attach signals to Agent Activity they create. This helps ensure that downstream behavior aligns with the sender’s expectations, whether it’s prompting a specific response type or adjusting how an action is displayed or prioritized.

Human-to-agent signals
Human-to-agent signals are signals set by human users on Agent Activities of type prompt. They provide additional context or intent that guides how an agent should interpret or respond to a user’s message.

These signals are only applicable to prompt-type Agent Activities.

stop
Applicable to Agent Activities of type prompt.

The stop signal instructs the agent to halt work immediately. From the moment this signal is received, the agent must not perform any further actions—such as making code changes, updates, or additional API calls.

After disengaging, the agent should emit a final activity—either of type response or error—to confirm that it has stopped and to inform the user of its current state.

An Agent Activity with the stop signal is generated when a user requests the agent to stop from within Linear.

An entry in a dropdown menu that reads "Send stop request"
Agent-to-human signals
Agents can include signals when emitting Agent Activities. Signals are added through the signal field, alongside the content field, to convey additional context or intent to human users.

auth
Applicable to Agent Activities of type elicitation.

The auth signal indicates that the agent requires the user to complete an account linking process before it can continue. When this signal is present, Linear renders a temporary UI state containing a link for the user to complete the account linking flow. This UI is ephemeral and will be dismissed once a newer agent-initiated activity is received.

After the required action is completed, the agent should resume work by emitting a thought activity.

Sample payload for agentActivityCreate mutation:

{
  agentSessionId: "...",
  content: {
    type: "elicitation",
    body: "Please authenticate to continue"
  },
  signal: "auth",
  signalMetadata: {
    url: "https://auth.example.com/oauth",
    userId: "...",        // Optional: restricts to a specific user
    providerName: "Orbit" // Optional: identifies the authentication provider
  }
}
A human user commenting "@Botcoder Please implement this", and a row below containing a button "Link account" and text "Link your account to continue."
Normal View – Targeted User
A human user commenting "@Botcoder Please implement this", and a row below containing "Waiting for (human username) to link their account."
Alt View – Non-target User
select
Applicable to Agent Activities of type elicitation.

The select signal presents a list of options for the user to choose from as part of an elicitation activity. It’s useful for confirmations, selecting a target (such as a GitHub repository), or any situation with multiple choices.

Users aren’t required to pick an option—they can reply in free text, which dismisses the elicitation. Any selected option is emitted as a regular prompt activity. And since responses may include natural language, your agent should always involve an LLM when interpreting the prompt.

Sample payload for agentActivityCreate mutation:

{
  agentSessionId: "...",
  content: {
    type: "elicitation",
    body: "Which repository is this issue about?"
  },
  signal: "select",
  signalMetadata: {
    options: [
      { value: "https://github.com/YOUR-ORG/YOUR-REPOSITORY" },
      { value: "https://github.com/YOUR-ORG/ANOTHER-REPOSITORY" }
      // ...
    ]
  }
}
If options are GitHub URLs, Linear automatically enriches them with icons and formatted names, so labels are not required.

Seek to:00:08 / Duration00:22


Integration Directory
Discover Linear add-ons or build your own

Linear icon next to integration icon
Overview
Linear's Integration Directory features apps and add-ons created by the Linear team as well as external applications. Install these to improve your workflow and sync with your favorite tools. You can also build your own integrations and submit them to the directory.

Basics
Linear crafted
If you see an integration with a star badge on the icon, that means it was crafted by the Linear team. You can install them via the link in the directory or by going to Settings > Workspace > Integrations and then select the integration name.

For most integrations, you'll have to be a workspace admin to install them for your workspace. If you don't know who is an admin, go to Settings > Workspace > Members and filter for Admins.

Third-party integrations
The directory also features integrations built by other apps and third parties. We recommend doing your own research into the integration owner and permissions required before installing these integrations. You can find the creator's website and contact in the sidebar.

Build your own
Use Linear's API to build your own integration and submit it to the directory following the instructions below. We recommend building applications using OAuth and having a separate workspace for the application, which gives all admins access to the application (instead of only the application creator).

We'll accept integrations that we think are useful to the community and are built by formal companies. We generally do not accept scripts or apps built by hobbyists, but feel free to reach out to integrations@linear.app if you think it should be included. You can also ask questions and see what others are building in our Slack community's #api channel.

Figma file screenshot of Linear integration template
Submit your integration
Fill out this form. It includes a sample page to give you a sense of copy style and length.
Submit assets to integrations@linear.app or include a link in the form. We've built a template in Figma to make this easy.
Send any questions to integrations@linear.app


Getting started
The Linear Typescript SDK exposes the Linear GraphQL schema through strongly typed models and operations. It’s written in Typescript but can also be used in any Javascript environment.

All operations return models, which can be used to perform operations for other models and all types are accessible through the Linear SDK package.

import { LinearClient, LinearFetch, User } from "@linear/sdk";
 
const linearClient = new LinearClient({ apiKey });
 
async function getCurrentUser(): LinearFetch<User> {
  return linearClient.viewer;
}
You can view the Linear SDK source code on GitHub.

Connect to the Linear API and interact with your data in a few steps:
1. Install the Linear Client
npm install @linear/sdk
2. Create a Linear client
SDK supports both authentication methods, personal API keys and OAuth 2. See authentication for more details.

You can create a client after creating authentication keys:

import { LinearClient } from '@linear/sdk'
 
// Api key authentication
const client1 = new LinearClient({
  apiKey: YOUR_PERSONAL_API_KEY
})
 
// OAuth2 authentication
const client2 = new LinearClient({
  accessToken: YOUR_OAUTH_ACCESS_TOKEN
})
3. Query for your issues
Using async await syntax:

async function getMyIssues() {
  const me = await linearClient.viewer;
  const myIssues = await me.assignedIssues();
 
  if (myIssues.nodes.length) {
    myIssues.nodes.map(issue => console.log(`${me.displayName} has issue: ${issue.title}`));
  } else {
    console.log(`${me.displayName} has no issues`);
  }
}
 
getMyIssues();
Or promises:

linearClient.viewer.then(me => {
  return me.assignedIssues().then(myIssues => {
    if (myIssues.nodes.length) {
      myIssues.nodes.map(issue => console.log(`${me.displayName} has issue: ${issue.title}`));
    } else {
      console.log(`${me.displayName} has no issues`);
    }
  });
});
Fetching & modifying data
Queries
Some models can be fetched from the Linear Client without any arguments:

const me = await linearClient.viewer;
const org = await linearClient.organization;
Other models are exposed as connections, and return a list of nodes:

const issues = await linearClient.issues();
const firstIssue = issues.nodes[0];
All required variables are passed as the first arguments:

const user = await linearClient.user("user-id");
const team = await linearClient.team("team-id");
Any optional variables are passed as the last argument as an object:

const fiftyProjects = await linearClient.projects({ first: 50 });
const allComments = await linearClient.comments({ includeArchived: true });
Most models expose operations to fetch other models:

const me = await linearClient.viewer;
const myIssues = await me.assignedIssues();
const myFirstIssue = myIssues.nodes[0];
const myFirstIssueComments = await myFirstIssue.comments();
const myFirstIssueFirstComment = myFirstIssueComments.nodes[0];
const myFirstIssueFirstCommentUser = await myFirstIssueFirstComment.user;
Parenthesis is required only if the operation takes an optional variables object.

You can find IDs for any entity within the Linear app by searching for "Copy model UUID" in the command menu.

Mutations
To create a model, call the Linear Client mutation and pass an input object:

const teams = await linearClient.teams();
const team = teams.nodes[0];
if (team.id) {
  await linearClient.createIssue({ teamId: team.id, title: "My Created Issue" });
}
To update a model, call the Linear Client mutation and pass in the required variables and input object:

const me = await linearClient.viewer;
if (me.id) {
  await linearClient.updateUser(me.id, { displayName: "Alice" });
}
Or call the mutation from the model:

const me = await linearClient.viewer;
await me.update({ displayName: "Alice" });
All mutations are exposed in the same way:

const projects = await linearClient.projects();
const project = projects.nodes[0];
if (project.id) {
  await linearClient.archiveProject(project.id);
  await project.archive();
}
Mutations will often return a success boolean and the mutated entity:

const commentPayload = await linearClient.createComment({ issueId: "some-issue-id" });
if (commentPayload.success) {
  return commentPayload.comment;
} else {
  return new Error("Failed to create comment");
}
Pagination
Connection models have helpers to fetch the next and previous pages of results:

const issues = await linearClient.issues({ after: "some-issue-cursor", first: 10 });
const nextIssues = await issues.fetchNext();
const prevIssues = await issues.fetchPrevious();
Pagination info is exposed and can be passed to the query operations. This uses the Relay Connection spec:

const issues = await linearClient.issues();
const hasMoreIssues = issues.pageInfo.hasNextPage;
const issuesEndCursor = issues.pageInfo.endCursor;
const moreIssues = await linearClient.issues({ after: issuesEndCursor, first: 10 });
Results can be ordered using the orderBy optional variable:

import { LinearDocument } from "@linear/sdk";
 
const issues = await linearClient.issues({ orderBy: LinearDocument.PaginationOrderBy.UpdatedAt });


Errors
Errors can be caught and inspected by wrapping the operation in a try catch block:

async function createComment(input: LinearDocument.CommentCreateInput): LinearFetch<Comment | UserError> {
  try {
    /** Try to create a comment */
    const commentPayload = await linearClient.createComment(input);
    /** Return it if available */
    return commentPayload.comment;
  } catch (error) {
    /** The error has been parsed by Linear Client */
    throw error;
  }
}
Or by catching the error thrown from a calling function:

async function archiveFirstIssue(): LinearFetch<ArchivePayload> {
  const me = await linearClient.viewer;
  const issues = await me.assignedIssues();
  const firstIssue = issues.nodes[0];
 
  if (firstIssue?.id) {
    const payload = await linearClient.archiveIssue(firstIssue.id);
    return payload;
  } else {
    return undefined;
  }
}
 
archiveFirstIssue().catch(error => {
  throw error;
});
The parsed error type can be compared to standard error types with instanceof to determine the course of action:

import { InvalidInputLinearError, LinearError, LinearErrorType } from '@linear/sdk'
import { UserError } from './custom-errors'
 
const input = { name: "Happy Team" };
createTeam(input).catch(error => {
  if (error instanceof InvalidInputLinearError) {
    /** If the mutation has failed due to an invalid user input return a custom user error */
    return new UserError(input, error);
  } else {
    /** Otherwise throw the error and handle in the calling function */
    throw error;
  }
});
Information about the request resulting in the error is attached if available:

run().catch(error => {
  if (error instanceof LinearError) {
    console.error("Failed query:", error.query);
    console.error("With variables:", error.variables);
  }
  throw error;
});
Information about the response is attached if available:

run().catch(error => {
  if (error instanceof LinearError) {
    console.error("Failed HTTP status:", error.status);
    console.error("Failed response data:", error.data);
  }
  throw error;
});
Any GraphQL errors are parsed and added to an array:

run().catch(error => {
  if (error instanceof LinearError) {
    console.log("The original error", error.raw);
  }
  throw error;
});
The raw error returned by the LinearGraphQLClient is still available:

run().catch(error => {
  if (error instanceof LinearError) {
    error.errors?.map(graphqlError => {
      console.log("Error message", graphqlError.message);
      console.log("LinearErrorType of this GraphQL error", graphqlError.type);
      console.log("Error due to user input", graphqlError.userError);
      console.log("Path through the GraphQL schema", graphqlError.path);
    });
  }
  throw error;
});
Previous


Advanced usage
The Linear Client wraps the Linear SDK, provides a LinearGraphQLClient, and parses errors.

Request Configuration
The LinearGraphQLClient can be configured by passing the RequestInit object to the Linear Client constructor:

const linearClient = new LinearClient({ apiKey, headers: { "my-header": "value" } });
Raw GraphQL Client
The LinearGraphQLClient is accessible through the Linear Client:

const graphQLClient = linearClient.client;
graphQLClient.setHeader("my-header", "value");
Raw GraphQL Queries
The Linear GraphQL API can be queried directly by passing a raw GraphQL query to the LinearGraphQLClient:

const graphQLClient = linearClient.client;
const cycle = await graphQLClient.rawRequest(`
  query cycle($id: String!) {
    cycle(id: $id) {
      id
      name
      completedAt
    }
  }`,
  { id: "cycle-id" }
);
Custom GraphQL Client
In order to use a custom GraphQL Client, the Linear SDK must be extended with a request function:

import { LinearError, LinearFetch, LinearRequest, LinearSdk, parseLinearError, UserConnection } from "@linear/sdk";
import { DocumentNode, GraphQLClient, print } from "graphql";
import { CustomGraphqlClient } from "./graphql-client";
 
/** Create a custom client configured with the Linear API base url and API key */
const customGraphqlClient = new CustomGraphqlClient("https://api.linear.app/graphql", {
  headers: { Authorization: apiKey },
});
 
/** Create the custom request function */
const customLinearRequest: LinearRequest = <Response, Variables>(
  document: DocumentNode,
  variables?: Variables
) => {
  /** The request must take a GraphQL document and variables, then return a promise for the result */
  return customGraphqlClient.request<Data>(print(document), variables).catch(error => {
    /** Optionally catch and parse errors from the Linear API */
    throw parseLinearError(error);
  });
};
 
/** Extend the Linear SDK to provide a request function using the custom client */
class CustomLinearClient extends LinearSdk {
  public constructor() {
    super(customLinearRequest);
  }
}
 
/** Create an instance of the custom client */
const customLinearClient = new CustomLinearClient();
 
/** Use the custom client as if it were the Linear Client */
async function getUsers(): LinearFetch<UserConnection> {
  const users = await customLinearClient.users();
  return users;
}

Advanced usage
The Linear Client wraps the Linear SDK, provides a LinearGraphQLClient, and parses errors.

Request Configuration
The LinearGraphQLClient can be configured by passing the RequestInit object to the Linear Client constructor:

const linearClient = new LinearClient({ apiKey, headers: { "my-header": "value" } });
Raw GraphQL Client
The LinearGraphQLClient is accessible through the Linear Client:

const graphQLClient = linearClient.client;
graphQLClient.setHeader("my-header", "value");
Raw GraphQL Queries
The Linear GraphQL API can be queried directly by passing a raw GraphQL query to the LinearGraphQLClient:

const graphQLClient = linearClient.client;
const cycle = await graphQLClient.rawRequest(`
  query cycle($id: String!) {
    cycle(id: $id) {
      id
      name
      completedAt
    }
  }`,
  { id: "cycle-id" }
);
Custom GraphQL Client
In order to use a custom GraphQL Client, the Linear SDK must be extended with a request function:

import { LinearError, LinearFetch, LinearRequest, LinearSdk, parseLinearError, UserConnection } from "@linear/sdk";
import { DocumentNode, GraphQLClient, print } from "graphql";
import { CustomGraphqlClient } from "./graphql-client";
 
/** Create a custom client configured with the Linear API base url and API key */
const customGraphqlClient = new CustomGraphqlClient("https://api.linear.app/graphql", {
  headers: { Authorization: apiKey },
});
 
/** Create the custom request function */
const customLinearRequest: LinearRequest = <Response, Variables>(
  document: DocumentNode,
  variables?: Variables
) => {
  /** The request must take a GraphQL document and variables, then return a promise for the result */
  return customGraphqlClient.request<Data>(print(document), variables).catch(error => {
    /** Optionally catch and parse errors from the Linear API */
    throw parseLinearError(error);
  });
};
 
/** Extend the Linear SDK to provide a request function using the custom client */
class CustomLinearClient extends LinearSdk {
  public constructor() {
    super(customLinearRequest);
  }
}
 
/** Create an instance of the custom client */
const customLinearClient = new CustomLinearClient();
 
/** Use the custom client as if it were the Linear Client */
async function getUsers(): LinearFetch<UserConnection> {
  const users = await customLinearClient.users();
  return users;
}