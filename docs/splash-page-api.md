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

## Implications for Automation

1. **Cannot manage splash pages via reefService** -- the Reef API has no splash page endpoints.
2. **Must interact with the DXP DSPM service directly** -- either via its own API or by driving the iframe UI.
3. **The `IFrameHandler` pattern** suggests the DSPM app communicates with the Pantheon parent via `postMessage`. This could be intercepted to understand the DSPM protocol.
4. **Next step**: Explore the DXP DSPM service directly at `https://dxp-dspm-prod.apps.int.drop.prod.us-west-2.aws.paas.redhat.com/` to discover its API, or intercept `postMessage` events between the iframe and Pantheon.
5. **Access control**: The splash page route requires `admin` or `splash-page-manager` permission.
