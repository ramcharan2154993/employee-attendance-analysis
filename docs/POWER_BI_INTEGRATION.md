# Microsoft Power BI Integration Architecture and Feasibility Guide

## 1. Executive Summary and Feasibility Assessment

This document evaluates the architectural feasibility, prerequisites, security boundaries, and step-by-step implementation roadmap for integrating Microsoft Power BI with the **Employee Attendance Analysis System**.

### Current Implementation State
- **Current Solution**: An interactive, Power BI-inspired analytics suite implemented entirely within Flask, Jinja2, Pandas, and Matplotlib. It renders dynamic KPI summary cards, monthly attendance and absence trend charts, status distributions (doughnut charts), department comparative benchmarks, and drill-down employee profiles (`/employees/<id>/analytics`).
- **Data Source**: Live, parameterized MySQL queries strictly respecting joining dates, active status, weekend exclusions, and organizational holidays.
- **Feasibility Verdict for Native Microsoft Power BI Embedded**: **Highly Feasible** via the **"App-Owns-Data"** architecture using Azure Active Directory (Entra ID) Service Principal authentication and Power BI REST APIs, without requiring end users to hold individual Power BI licenses.

---

## 2. Power BI Embedded Architecture: App-Owns-Data

For an enterprise internal HR web portal, the recommended integration pattern is **App-Owns-Data (Embed for your customers/organization)**:

```
+-----------------------------------------------------------------------------------+
|                                 Client Browser                                    |
|   +---------------------------------------------------------------------------+   |
|   |   Flask HR Portal (/reports or /employees/<id>/analytics)                 |   |
|   |   +-------------------------------------------------------------------+   |   |
|   |   |  Power BI JS SDK (iframe) <--- Encrypted Embed Token + Embed URL  |   |   |
|   +---+-------------------------------------------------------------------+---+---+
                                          |
                        1. Authenticated User Request
                                          v
+-----------------------------------------------------------------------------------+
|                             Flask Backend Application                             |
|  - Validates session & role (Admin / HR)                                          |
|  - Calls MSAL Python with Client ID & Client Secret                               |
|  - Obtains Azure AD OAuth2 Token                                                  |
|  - Calls Power BI REST API to generate Embed Token with RLS identities            |
|  - Passes Embed Token + Report ID + Embed URL to Jinja template                   |
+-----------------------------------------------------------------------------------+
             |                                                  |
  2. OAuth2 / Client Creds                        3. REST: GenerateTokenInGroup
             v                                                  v
+-------------------------+                       +---------------------------------+
|     Microsoft Entra ID  |                       |      Power BI Cloud Service     |
|    (Service Principal)  |                       |  - App Workspace                |
+-------------------------+                       |  - PBIX Semantic Model / Report |
                                                  +---------------------------------+
                                                                    |
                                                      4. DirectQuery or Gateway
                                                                    v
                                                  +---------------------------------+
                                                  |        MySQL Database           |
                                                  |   (attendance_db / replica)     |
                                                  +---------------------------------+
```

---

## 3. Azure & Power BI Service Setup Requirements

### 3.1 Azure Active Directory (Entra ID) Registration
1. Register an Application in the Azure Portal:
   - Application Name: `Employee-Attendance-PowerBI-Bridge`
   - Supported Account Types: Accounts in this organizational directory only (Single tenant).
2. Generate Application Secret:
   - Create a Client Secret under **Certificates & secrets** and record the `Value` securely in `.env` as `POWERBI_CLIENT_SECRET`.
   - Record `Application (client) ID` as `POWERBI_CLIENT_ID` and `Directory (tenant) ID` as `POWERBI_TENANT_ID`.
3. Create an Azure AD Security Group:
   - Name: `PowerBI-Embedded-Service-Principals`.
   - Add the registered Application Service Principal as a member of this security group.

### 3.2 Power BI Admin Portal Configuration
1. Sign in to [Power BI Admin Portal](https://app.powerbi.com/admin-portal).
2. Navigate to **Tenant Settings** -> **Developer Settings**:
   - Enable **Embed content in apps**.
   - Enable **Allow service principals to use Power BI APIs**.
   - Scope access specifically to the security group `PowerBI-Embedded-Service-Principals`.
3. Workspace Permission:
   - Create a dedicated Power BI Workspace (e.g., `HR Workforce Analytics`).
   - Grant the Service Principal **Admin** or **Member** role on this workspace.

---

## 4. Database Connection and Refresh Architecture

### Option A: DirectQuery via On-Premises Data Gateway (Recommended for Live Attendance)
- **Mechanism**: Power BI queries the MySQL database in real time whenever an HR user interacts with slicers or filters.
- **Requirements**:
  - Deploy the Microsoft On-Premises Data Gateway on a server with network visibility to the MySQL host (port 3306).
  - Install MySQL Connector/NET or MySQL ODBC driver on the gateway machine.
  - In Power BI Service, configure the Gateway Data Source connection pointing to `attendance_db`.

### Option B: Scheduled Refresh / Semantic Model Import
- **Mechanism**: Power BI imports data into VertiPaq storage on a scheduled interval (e.g., hourly or every 30 minutes).
- **Pros/Cons**: Ultra-fast interactive rendering; however, newly recorded bulk attendance has a latency up to the refresh interval.

---

## 5. Flask Backend Integration (Python MSAL)

To integrate Power BI report embedding without exposing credentials to the client:

### 5.1 Environment Configuration (`.env`)
```env
POWERBI_TENANT_ID=00000000-0000-0000-0000-000000000000
POWERBI_CLIENT_ID=00000000-0000-0000-0000-000000000000
POWERBI_CLIENT_SECRET=your_azure_client_secret_here
POWERBI_WORKSPACE_ID=00000000-0000-0000-0000-000000000000
POWERBI_REPORT_ID=00000000-0000-0000-0000-000000000000
```

### 5.2 Token Acquisition and Embed Token Generation
```python
import os
import requests
import msal

def get_powerbi_embed_data(user_id: int, role: str, department: str | None = None) -> dict:
    """Acquire Azure AD access token and generate Power BI embed token with Row-Level Security (RLS)."""
    client_id = os.getenv("POWERBI_CLIENT_ID")
    client_secret = os.getenv("POWERBI_CLIENT_SECRET")
    tenant_id = os.getenv("POWERBI_TENANT_ID")
    workspace_id = os.getenv("POWERBI_WORKSPACE_ID")
    report_id = os.getenv("POWERBI_REPORT_ID")

    authority_url = f"https://login.microsoftonline.com/{tenant_id}"
    scope = ["https://analysis.windows.net/powerbi/api/.default"]

    cca = msal.ConfidentialClientApplication(
        client_id,
        authority=authority_url,
        client_credential=client_secret
    )
    token_response = cca.acquire_token_for_client(scopes=scope)
    if "access_token" not in token_response:
        raise RuntimeError(f"Power BI authentication failed: {token_response.get('error_description')}")

    aad_token = token_response["access_token"]
    headers = {
        "Authorization": f"Bearer {aad_token}",
        "Content-Type": "application/json"
    }

    # Generate Embed Token with optional Row-Level Security (RLS)
    token_request_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}/GenerateToken"
    body = {
        "accessLevel": "View",
        "identities": [
            {
                "username": str(user_id),
                "roles": [role],
                "datasets": ["<dataset_id>"]
            }
        ]
    }

    resp = requests.post(token_request_url, headers=headers, json=body, timeout=10)
    resp.raise_for_status()
    embed_token_data = resp.json()

    # Get Report Embed URL
    report_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}"
    rep_resp = requests.get(report_url, headers=headers, timeout=10)
    rep_resp.raise_for_status()
    report_data = rep_resp.json()

    return {
        "embed_token": embed_token_data["token"],
        "embed_url": report_data["embedUrl"],
        "report_id": report_id,
        "token_expiry": embed_token_data["expiration"]
    }
```

---

## 6. Frontend Embedding and Content Security Policy (CSP)

To embed the Power BI canvas into Jinja templates without violating strict enterprise security standards:

### 6.1 Content Security Policy Adjustment
The current strict CSP:
```
default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'
```
To support Power BI Embedded, the CSP must be configured to permit Microsoft Power BI iframe hosting and telemetry endpoints:
```
default-src 'self'; 
frame-src https://app.powerbi.com; 
script-src 'self' https://app.powerbi.com; 
connect-src 'self' https://api.powerbi.com https://wabi-*.analysis.windows.net; 
style-src 'self' 'unsafe-inline'; 
img-src 'self' data: https://app.powerbi.com;
```

### 6.2 Frontend Container (`powerbi_embed.html`)
Using standard vanilla JavaScript or the Power BI JavaScript client:
```html
<div id="reportContainer" style="width: 100%; height: 750px; border: 1px solid var(--border); border-radius: 8px;"></div>

<script src="/static/js/powerbi.min.js"></script>
<script>
    const models = window['powerbi-client'].models;
    const config = {
        type: 'report',
        tokenType: models.TokenType.Embed,
        accessToken: "{{ embed_data.embed_token }}",
        embedUrl: "{{ embed_data.embed_url }}",
        id: "{{ embed_data.report_id }}",
        permissions: models.Permissions.View,
        settings: {
            panes: {
                filters: { expanded: false, visible: true },
                pageNavigation: { visible: true }
            },
            background: models.BackgroundType.Transparent
        }
    };
    const reportContainer = document.getElementById('reportContainer');
    const report = powerbi.embed(reportContainer, config);
</script>
```

---

## 7. Row-Level Security (RLS) Rules

To enforce data boundary segregation in Power BI reports:
- **Admin Role**: No RLS filter; can see all departments, audit logs, and company-wide metrics.
- **HR Department Role**: DAX filter applied to the `Employees` semantic table:
  ```dax
  [Department] = USERNAME() || [Department] = LOOKUPVALUE(Users[Department], Users[Username], USERNAME())
  ```
- **Active Roster Filter**: Enforce consistent business logic:
  ```dax
  [IsActive] == TRUE() && [JoiningDate] <= TODAY()
  ```

---

## 8. Licensing and Cost Considerations

1. **Development Phase**:
   - Requires one **Power BI Pro** license (~$10/user/month) for the report author to design and publish reports in Power BI Desktop and manage the workspace.
2. **Production Embedded Capacity ("App-Owns-Data")**:
   - Requires an **Azure Power BI Embedded Capacity (A SKU)** (e.g., A1 SKU starting at ~$1.00/hour, pauseable when idle) or a **Microsoft Fabric Capacity (F SKU)**.
   - End users accessing reports via the Flask portal do **not** require individual Power BI licenses.
3. **Alternative "User-Owns-Data"**:
   - Every single HR operator and viewer requires an active Microsoft 365 / Power BI Pro license ($10/user/month). Not recommended when scaling across a wider internal organization.

---

## 9. Migration Roadmap and Checklist

| Phase | Milestone | Deliverables | Dependencies |
| :--- | :--- | :--- | :--- |
| **Phase 1** (Current) | **Native Flask Analytics Suite** | Dynamic Matplotlib charts, KPI summary cards, employee profile drill-down, 100% database-backed calculations. | None. Verified in production. |
| **Phase 2** | **Azure & Workspace Provisioning** | Entra ID App registration, Client Secret, Power BI Admin API delegation, dedicated Workspace setup. | Azure Subscription + Power BI Pro author license. |
| **Phase 3** | **Semantic Model & DirectQuery** | PBIX development matching exact Flask formulas: `Eligible = Present + Absent + Leave`. DirectQuery over MySQL Gateway. | On-Premises Data Gateway host. |
| **Phase 4** | **Flask MSAL Backend Service** | Implement `src/powerbi.py` with `get_powerbi_embed_data()`. Add `/reports/powerbi` route. | MSAL Python library. |
| **Phase 5** | **Frontend Embedding & CSP** | Adjust CSP headers, integrate `powerbi.min.js`, verify RLS and responsive container styling. | CSP security review. |

---

## 10. Summary

The application is completely prepared for Microsoft Power BI Embedded. In the interim, all metrics, distribution charts, trends, and drill-downs are fully functional and live in the native Flask dashboard, guaranteeing that users currently receive immediate, verified reporting with zero license overhead.
