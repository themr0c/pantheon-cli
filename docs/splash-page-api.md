# Splash Page API Reference

Findings from exploring the Pantheon splash page management interface.

## Architecture: Iframe to a Separate Microservice

The splash page in Pantheon is **not managed by the Reef API or reefService**. Instead, the Pantheon Angular app embeds an **iframe** pointing to a completely separate microservice called **DXP DSPM** (Splash Page Manager).

### How It Works

1. Pantheon defines a route `/splash-pages/:appPath*` handled by `SplashPagesCtrl`
2. The controller reads `pantheonConfig.splashPagesServiceUrl` (configured from `window.__conf.spmUrl`)
3. It constructs an iframe URL: `{splashPagesServiceUrl}product/{product}/{version}/{environment}?iframe=true`
4. The iframe loads the DXP DSPM app, which runs its own separate UI for splash page management

### Key URLs

| Environment | Splash Page Manager URL |
|---|---|
| Production | `https://dxp-dspm-prod.apps.int.drop.prod.us-west-2.aws.paas.redhat.com/` |
| Configured example (1.9/stage) | `https://dxp-dspm-prod.apps.int.drop.prod.us-west-2.aws.paas.redhat.com/product/red_hat_developer_hub/1.9/stage?iframe=true` |
| Unconfigured example (1.10/stage) | `https://dxp-dspm-prod.apps.int.drop.prod.us-west-2.aws.paas.redhat.com/product/red_hat_developer_hub/1.10/stage?iframe=true` |

### SplashPagesCtrl Source (de-minified)

```javascript
// Injected: $scope, $routeParams, $sce, pantheonConfig, IFrameHandler
function SplashPagesCtrl($scope, $routeParams, $sce, pantheonConfig, IFrameHandler) {
    $scope.view = "splash-pages";

    var baseUrl = pantheonConfig.splashPagesServiceUrl + "product";

    // Build iframe URL from route params
    var iframeUrl = baseUrl;
    if ($routeParams.appPath) {
        iframeUrl += "/" + $routeParams.appPath;
    }
    iframeUrl += "?iframe=true";

    $scope.iframeSrc = $sce.trustAsResourceUrl(iframeUrl);

    // Cross-origin iframe communication handler
    var url = new URL(baseUrl);
    $scope.iframeHandler = new IFrameHandler(url.origin, url.pathname);
    $scope.iframeHandler.start();

    $scope.$on("$destroy", function() {
        $scope.iframeHandler.stop();
    });
}
```

### Splash Page Template

```html
<div ng-show="!iframeHandler.loaded">
    <div class="spinner spinner-lg"></div>
    <div class="text-center">Loading...</div>
    <br>
</div>

<div ng-show="iframeHandler.loaded">
    <iframe id="splash-page-frame"
            ng-src="{{iframeSrc}}"
            class="splash-page-frame">
    </iframe>
</div>
```

## reefService: No Splash Methods

The `reefService` has **59 own methods** and **zero** are related to splash pages, categories, or promotions. Splash page management is entirely delegated to the DXP DSPM service.

### Complete reefService Method List

**Title Management:**
- `createTitle`, `createTitleLocale`, `cloneTitle`, `updateTitle`
- `getTitles`, `getTitlesBasic`, `getTitleByUrl`, `getTitleEnv`
- `getTitleEnvBuildConfig`, `updateTitleEnvBuildConfig`
- `deleteLightblueTitle`, `renameLightblueTitle`
- `publishTitle`, `resetTitles`
- `addMetaData`, `getTitlesSearchQuery`

**Jenkins/Build:**
- `createJenkinsJob`, `deleteJenkinsJob`, `renameJenkinsJob`
- `getJenkinsJob`, `getJenkinsJobLog`
- `startJenkinsJob`, `toggleJenkinsJob`
- `getJenkinsBuildingJobs`
- `startWatchingJenkinsBuildingJobs`, `stopWatchingJenkinsBuildingJobs`
- `startWatchingTitleBuildingJobs`, `stopWatchingTitleBuildingJobs`
- `generateJenkinsJobName`

**Jenkins Packaging:**
- `createJenkinsPackagingJob`, `deleteJenkinsPackagingJob`
- `getJenkinsPackagingJob`, `getJenkinsPackagingJobs`
- `startJenkinsPackagingJob`, `toggleJenkinsPackagingJob`
- `generateJenkinsPackagingJobName`, `resetJenkinsPackagingJobs`

**Jenkins Views:**
- `getJenkinsProductViews`, `createJenkinsProductView`
- `createMissingJenkinsProductViews`, `resetJenkinsProductViews`

**Product/Version:**
- `getProducts`, `getProductVersions`, `createProductVersion`
- `resetProducts`
- `renameLightblueProduct`, `renameAllLightblueProducts`

**GitLab:**
- `getGitLabGroups`, `getGitLabGroupProjects`, `getGitLabProject`
- `createGitLabProject`, `createGitLabBranch`
- `addGitLabDeployKey`, `addGitLabFiles`, `addGitLabProjectHook`
- `pushNewGitRepo`

**Other:**
- `getInfo`, `getBrewTitle`

## Angular Routes

### Splash-Related Routes

| Route | Controller | Template | Permissions |
|---|---|---|---|
| `/splash-pages` | `SplashPagesCtrl` | `/modules/splash-pages/views/splash-pages.html` | `admin`, `splash-page-manager` |
| `/splash-pages/:appPath*` | `SplashPagesCtrl` | (same) | `admin`, `splash-page-manager` |

The `appPath` parameter captures the full path including product, version, and environment (e.g., `red_hat_developer_hub/1.9/stage`).

### Other Notable Routes

| Route | Purpose |
|---|---|
| `/titles/:product/:version` | Title management (where we use reefService) |
| `/packaging` | Packaging builds |
| `/translations/:lang` | Translation management |
| `/admin` | User/role/system administration |

## Title Data Structure

Titles from the Reef API (`lightblue/get_titles`) have **no splash/category fields**. All 33 titles for version 1.9 are "uncategorized" from the Reef API perspective. The categorization and ordering of titles on the splash page is managed entirely by the DXP DSPM service.

### Title Keys (from Reef API)

```
buildConfig, environments, gitUrl, jobs, language,
name, product_id, urlFragment, urlFragmentAlias, uuid
```

No `category`, `splashCategory`, `order`, `promoted`, or similar fields exist in the title data.

## Reef API Endpoints Probed (All 404)

The following endpoints were tried and all returned 404, confirming splash page data is not in the Reef API:

- `lightblue/get_splash_page`
- `lightblue/get_splash_pages`
- `lightblue/splash_page`
- `splash`
- `splash_page`
- `lightblue/get_categories`
- `lightblue/categories`

## pantheonConfig Constants

From the JS bundle (`main.75223247f5.bundle.js`):

```javascript
constant("pantheonConfig", {
    reefServiceUrl: getServiceUrl("reef"),         // window.__conf.reefUrl
    pantheonServiceUrl: getServiceUrl("pantheon"),  // window.__conf.pantheonUrl
    splashPagesServiceUrl: getServiceUrl("splash-pages"),  // window.__conf.spmUrl
    isLocalHost: ...,
    sourceLang: "en-US",
    langs: [/* ja-JP, es-ES, pt-BR, fr-FR, de-DE, zh-CN, zh-TW, it-IT, ko-KR, ru-RU */]
})
```

## DXP DSPM Internal Architecture

The DXP DSPM is a **Drupal 10** application ("Docs 2.0 Splash Page Manager") using:
- Custom theme: `spm` (PatternFly UI components)
- Custom module: `product_manager` (category management, tabledrag)
- Custom module: `pantheon_messaging` (postMessage to parent iframe)
- Standard Drupal Form API for all operations

### Drupal Form: `product_manager_view_product`

The main splash page is a single Drupal form (`form_id: product_manager_view_product`) containing:

**Controls:**
- `versions` (select) — version/environment selector
- `filter_localizations` (select) — locale filter
- `filter_targets` (select) — target filter
- `add_category[category]` (select) — add a category from available list
- `action` (select) — bulk action ("remove")
- `status_direction` (select) — status management
- `embargo_date[date]` / `embargo_date[time]` — embargo scheduling

**CSRF tokens:**
- `form_build_id` — unique per page render
- `form_token` — CSRF protection
- `form_id` — always `product_manager_view_product`

**Category data structure (hidden fields):**
```
categories[{uuid}][title][id]       = {uuid}           # Category UUID
categories[{uuid}][title][parent]   = ""                # Empty for top-level
categories[{uuid}][title][depth]    = "0"               # 0 for categories
categories[{uuid}][weight]          = {integer}         # Display order

categories[link--{uuid}--{index}][title][id]     = link--{uuid}--{index}
categories[link--{uuid}--{index}][title][parent] = {uuid}     # Parent category UUID
categories[link--{uuid}--{index}][title][depth]  = "1"        # 1 for links
categories[link--{uuid}--{index}][weight]        = {integer}  # Order within category
categories[link--{uuid}--{index}][action_select] = "1"        # Checkbox for bulk actions
```

### 1.9/stage Categories (Current)

| Weight | UUID | Category | Titles |
|--------|------|----------|--------|
| 83 | 20fd5ed2-... | Discover | About Red Hat Developer Hub |
| 84 | 28327e71-... | Release Notes | Red Hat Developer Hub release notes |
| 85 | 70d1b236-... | Get started | Setting up..., Navigate... |
| 86 | 9343a97b-... | Install | Air-gapped, EKS, GKE, AKS, OCP, OSD |
| 87 | (uuid) | Upgrade | Upgrading Red Hat Developer Hub |
| 88 | (uuid) | Configure | Configuring..., Customizing... |
| 89 | (uuid) | Control access | Authentication..., Authorization... |
| 90 | (uuid) | Integrate | GitHub, MCP tools, Lightspeed, OpenShift AI Connector |
| 91 | (uuid) | Manage | Scorecards, TechDocs, Software dev... |
| 92 | (uuid) | Monitor | Adoption Insights, Audit logs, Monitoring, Telemetry |
| 93 | (uuid) | Automate | Orchestrator |
| 94 | 2bd7ccda-... | Plugins | Installing/viewing, Configuring, Using, Develop/deploy, Reference |

### Operations via Drupal AJAX

The DSPM uses Drupal AJAX for operations. Each action has a unique selector mapped to an AJAX endpoint:

```
/product/{product}/{version}/{title_uuid}/{action_type}/{param}?destination=...&iframe=true
```

Action types discovered:
- `0/1` through `5/1` — various link operations per category
- Modal dialogs for "Add link", "Edit link", "Edit category"
- Bulk remove via `action` select + checkbox selection

### Buttons/Operations Available

- **Save** — submits the main form
- **Add category** — select from `add_category[category]` dropdown + click add
- **Remove category** — per-category remove button
- **Add link** — opens modal dialog (AJAX)
- **Edit link** / **Remove link** — per-link operations (AJAX)
- **Promote to Production** — dropdown action
- **Copy from Production** — dropdown action
- **Show row weights** — toggles drag-and-drop vs weight numbers

## Automation Approach

### Hybrid pattern (from `reef-publish.py` insight)

Use Playwright **only for initial Kerberos SPNEGO login**, then extract cookies and use `requests` for all subsequent API/form operations:

1. **Login phase** (Playwright Firefox, headed if needed):
   - Navigate to Pantheon, handle SSO/SPNEGO
   - Extract session cookies after successful auth
   - Cache cookies (same pattern as `reef-publish.py`)

2. **Export phase** (`requests` with cached cookies):
   - GET `https://dxp-dspm-prod.../product/{product}/{version}/{env}?iframe=true`
   - Parse HTML form to extract category structure (UUID, weight, parent, titles)
   - Output YAML configuration file

3. **Configure phase** (`requests` with cached cookies):
   - GET the form page to obtain `form_build_id` and `form_token`
   - Build POST data matching the Drupal form structure
   - POST to save changes (categories, ordering, links)

This avoids the overhead of running Playwright for every operation and allows headless-first operation.

### Access control

The splash page route requires `admin` or `splash-page-manager` permission.
