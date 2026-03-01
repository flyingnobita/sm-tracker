# Specification: Instagram Graph API Integration

## Overview

The `sm-tracker` tool needs to track Instagram follower and following counts. The initial attempt using the `instaloader` library was unviable due to aggressive rate-limiting (`429 Too Many Requests`) by Instagram.

This specification outlines the migration to the official **Meta Graph API**, which provides a stable, authorized method for retrieving this data, provided the user meets specific account and linking requirements.

## Technical Requirements

1. **Dependency Removal:** Drop `instaloader` from `pyproject.toml` to reduce brittle third-party scraping dependencies.
2. **HTTP Client:** Utilize Python's built-in `urllib.request` to interact with the Graph API, preventing the need for heavy external HTTP libraries (like `requests`).
3. **Authentication:** The integration must use a Facebook Developer App User Access Token.
4. **Target Account Identification:** The API requires a Meta Graph Object ID for the Instagram Business Account, which is distinct from a public Instagram username or standard user ID.
5. **Environment Variables (`.env`)**:
    - `INSTAGRAM_ACCOUNT_ID`: (Required) The internal Meta Graph ID of the connected Instagram Professional account.
    - `LONG_LIVED_USER_TOKEN`: (Required) The User Access Token generated via the Facebook Developer portal.
    - `INSTAGRAM_USERNAME`: (Optional) If provided, the tracker will use the `business_discovery` edge to fetch data for this competitor handle. If omitted, it fetches data for the authenticated `INSTAGRAM_ACCOUNT_ID`.

## Implementation Details

### API Endpoints Used

**1. Fetching Own Account Data (No `INSTAGRAM_USERNAME`)**

```http
GET https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}?fields=followers_count,follows_count&access_token={LONG_LIVED_USER_TOKEN}
```

**2. Fetching Competitor Data (Using `INSTAGRAM_USERNAME`)**

```http
GET https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}?fields=business_discovery.username({INSTAGRAM_USERNAME}){followers_count,follows_count}&access_token={LONG_LIVED_USER_TOKEN}
```

### Response Handling

- Parse the JSON response.
- If the response contains an `error` object, raise a `RuntimeError` with the specific Graph API HTTP status code, error message, and subcode for easy troubleshooting.
- Return a `PlatformCounts` object containing the extracted `followers_count` and `follows_count` (mapped to `followers` and `following`).

## Setup Guide & Linking Requirements

_This section documents the precise, verified steps required for a user to obtain the required credentials. Standard Facebook linking is insufficient._

### 1. Account Prerequisites

1. **Instagram Professional Account:** The Instagram account _must_ be converted to a Creator or Business account in the Instagram mobile app settings.
2. **Facebook Page:** A published Facebook Page must exist (it can be empty).

### 2. Meta Business Suite Linking (Critical Step)

Linking the Instagram account via the standard Facebook Page UI or the Instagram app is often insufficient for Graph API visibility. It must be linked via Meta Business Suite.

1. Navigate to **Meta Business Suite** (`business.facebook.com`).
2. Go to **Settings** -> **Accounts**.
3. Ensure both the Facebook Page and the Instagram account are present in their respective tabs.
4. Under **Pages**, select your Page and click **Connect assets**. Explicitly link the Instagram account asset to the Page asset.

### 3. Token Generation

1. Go to the **Meta for Developers** portal and create an App.
2. Open the **Graph API Explorer**.
3. Select your App and choose **User Token**.
4. Add the following permissions:
    - `instagram_basic`
    - `instagram_manage_insights`
    - `pages_show_list`
    - `pages_read_engagement`
    - **`business_management`** _(Crucial for retrieving the account ID)_
5. Click **Generate Access Token**.
6. During the OAuth popup, ensure you click "Edit Settings" and check the boxes for _both_ your Facebook Page and your linked Instagram account.

### 4. Extracting the Graph ID

1. In the Graph API Explorer, set the query to:
   `me/accounts?fields=instagram_business_account,name`
2. Submit the query.
3. Locate the `"instagram_business_account"` object in the JSON response. The `"id"` within this object is the required `INSTAGRAM_ACCOUNT_ID`.
4. _(Note: Do not use the `id` of the Facebook Page itself, nor a standard Instagram user ID from a lookup tool)._
