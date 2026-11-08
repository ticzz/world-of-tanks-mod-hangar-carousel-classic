[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PackagePath
)

$ErrorActionPreference = 'Stop'
$PackagePath = [IO.Path]::GetFullPath($PackagePath)
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::OpenRead($PackagePath)
try {
    $names = @($zip.Entries | ForEach-Object FullName)
    $nativeBundlePath = if ($names -contains 'res/gui/gameface/_dist/production/mono/hangar/main/bundle.js') {
        'res/gui/gameface/_dist/production/mono/hangar/main/bundle.js'
    }
    elseif ($names -contains 'res/gui/gameface/_dist/production/mono/hangar/views/main/main.html/bundle.js') {
        'res/gui/gameface/_dist/production/mono/hangar/views/main/main.html/bundle.js'
    }
    else {
        throw 'Native hangar bundle is missing from the package.'
    }
    $comp7BundlePath = if ($names -contains 'res/comp7/gui/gameface/_dist/production/mono/lobby/hangar/bundle.js') {
        'res/comp7/gui/gameface/_dist/production/mono/lobby/hangar/bundle.js'
    }
    elseif ($names -contains 'res/comp7/gui/gameface/_dist/production/mono/lobby/views/hangar/hangar.html/bundle.js') {
        'res/comp7/gui/gameface/_dist/production/mono/lobby/views/hangar/hangar.html/bundle.js'
    }
    else {
        throw 'Comp7 hangar bundle is missing from the package.'
    }
    $frontlineBundlePath = 'res/frontline/gui/gameface/_dist/production/mono/lobby/hangar/bundle.js'
    $tooltipBundlePath = if ($names -contains 'res/gui/gameface/_dist/production/mono/hangar/vehicle_tooltip/bundle.js') {
        'res/gui/gameface/_dist/production/mono/hangar/vehicle_tooltip/bundle.js'
    }
    elseif ($names -contains 'res/gui/gameface/_dist/production/mono/hangar/views/vehicle_tooltip/vehicle_tooltip.html/bundle.js') {
        'res/gui/gameface/_dist/production/mono/hangar/views/vehicle_tooltip/vehicle_tooltip.html/bundle.js'
    }
    else {
        throw 'Native vehicle tooltip bundle is missing from the package.'
    }
    $required = @(
        'meta.xml',
        'res/scripts/client/gui/mods/mod_hangar_carousel_classic.pyc',
        'res/gui/gameface/mods/hcc/hangar_carousel_classic/hangar_carousel_classic.js',
        'res/gui/gameface/mods/hcc/hangar_carousel_classic/hangar_carousel_classic.css',
        'res/gui/gameface/mods/hcc/hangar_carousel_classic/hangar_carousel_classic.tooltip.js',
        'res/gui/gameface/mods/hcc/hangar_carousel_classic/hangar_carousel_classic.tooltip.css',
        $nativeBundlePath,
        $comp7BundlePath,
        $frontlineBundlePath,
        $tooltipBundlePath,
        'res/gui/gameface/_dist/production/mono/hangar/vehicle_tooltip/vehicle_tooltip.css'
    )
    foreach ($entry in $required) {
        if ($entry -notin $names) {
            throw "Required package entry is missing: $entry"
        }
    }

    if ($names -contains 'res/gui/gen_resources/hangar_carousel_classic.json') {
        throw 'Obsolete standalone HCC layout found; HCC injects assets into the native carousel model.'
    }

    $pyc = $zip.GetEntry('res/scripts/client/gui/mods/mod_hangar_carousel_classic.pyc')
    $stream = $pyc.Open()
    try {
        $header = New-Object byte[] 4
        [void]$stream.Read($header, 0, 4)
    }
    finally {
        $stream.Dispose()
    }
    $magic = ($header | ForEach-Object { $_.ToString('X2') }) -join '-'
    if ($magic -ne '03-F3-0D-0A') {
        throw "Unexpected Python bytecode magic: $magic (expected Python 2.7)."
    }

    $js = $zip.GetEntry('res/gui/gameface/mods/hcc/hangar_carousel_classic/hangar_carousel_classic.js')
    $jsStream = $js.Open()
    $reader = New-Object IO.StreamReader($jsStream, [Text.Encoding]::UTF8)
    try {
        $jsSource = $reader.ReadToEnd()
    }
    finally {
        $reader.Dispose()
        $jsStream.Dispose()
    }
    if ($jsSource.Contains(':scope')) {
        throw 'Unsupported Gameface CSS selector found: :scope'
    }
    if ($jsSource.Contains('Page_carouselButtons_')) {
        throw 'Classic controls must not be rendered beside the carousel.'
    }
    if ($jsSource.Contains('createElement("select")')) {
        throw 'Native Gameface does not render an HTML select compactly; use icon controls.'
    }
    if (-not $jsSource.Contains('carouselRowButtonContent') -or
        -not $jsSource.Contains('labels().carousel_auto') -or
        -not $jsSource.Contains('SORT_ICONS') -or
        -not $jsSource.Contains('SORT_DIRECTION_ICONS')) {
        throw 'Carousel row icon controls or automatic mode UI are missing.'
    }
    if ($jsSource.Contains('-webkit-text-fill-color')) {
        throw 'Unsupported Gameface text-fill property found.'
    }
    if (-not $jsSource.Contains('onSetSorting') -or
        -not $jsSource.Contains('applyActionCardsVisibility')) {
        throw 'Native sorting controls or action-card visibility support are missing.'
    }
    if ($jsSource.Contains('CurrencyLock') -or
        $jsSource.Contains('hcp-currency-lock')) {
        throw 'Currency protection must not be included in this classic carousel mod.'
    }

    $nativeBundle = $zip.GetEntry($nativeBundlePath)
    $nativeStream = $nativeBundle.Open()
    $nativeReader = New-Object IO.StreamReader($nativeStream, [Text.Encoding]::UTF8)
    try {
        $nativeSource = $nativeReader.ReadToEnd()
    }
    finally {
        $nativeReader.Dispose()
        $nativeStream.Dispose()
    }
    if (-not (
            $nativeSource.Contains('t+=v)e.push(j.slice(t,t+v))') -or
            $nativeSource.Contains('t+=i)e.push(j.slice(t,t+i))') -or
            $nativeSource.Contains('a+=_)t.push(e.slice(a,a+_))')
        )) {
        throw 'Native carousel bundle does not contain the generic row chunker.'
    }
    if ($nativeSource.Contains('totalElements:2===v?N.length:w.length') -or
        $nativeSource.Contains('totalElements:2===_?b.length:v.length')) {
        throw 'Native carousel bundle still contains the two-row-only renderer.'
    }
    if (-not (
            $nativeSource.Contains('3===s&&"hcc-native-carousel--3",4===s&&"hcc-native-carousel--4"') -or
            $nativeSource.Contains('3===v&&"hcc-native-carousel--3",4===v&&"hcc-native-carousel--4"') -or
            $nativeSource.Contains('3===_&&"hcc-native-carousel--3",4===_&&"hcc-native-carousel--4"')
        )) {
        throw 'Native carousel bundle does not expose the three- and four-row height classes.'
    }
    if (-not $nativeSource.Contains('hccSortJson') -or
        -not $nativeSource.Contains('const hcc=') -or
        -not (
            $nativeSource.Contains('hccCarouselAuto:i.hccCarouselAuto') -or
            $nativeSource.Contains('hccCarouselAuto:r.hccCarouselAuto')
        )) {
        throw 'Native carousel bundle does not contain Classic sorting support.'
    }
    if (-not (
            $nativeSource.Contains('hccCarouselAuto.get()?(u.length<=8?1:u.length<=16?2:u.length<=24?3:4)') -or
            $nativeSource.Contains('hccCarouselAuto.get()?(l.length<=8?1:l.length<=16?2:l.length<=24?3:4)')
        )) {
        throw 'Native carousel bundle does not calculate automatic rows from the final vehicle list.'
    }
    if (-not (
            $nativeSource.Contains('hccCarouselAuto.get()?(ir().model.current.amount()<=8?1:ir().model.current.amount()<=16?2:ir().model.current.amount()<=24?3:4)') -or
            $nativeSource.Contains('hccCarouselAuto.get()?(l.length<=8?1:l.length<=16?2:l.length<=24?3:4)')
        )) {
        throw 'Native carousel page does not calculate automatic height from the final vehicle list.'
    }
    if (-not $nativeSource.Contains('3===s&&"hcc-native-carousel-page--3",4===s&&"hcc-native-carousel-page--4"')) {
        throw 'Native carousel page does not expose the three- and four-row layout classes.'
    }
    if (-not (
        $nativeSource.Contains('if(!s&&O(t)&&!a?.fromWotPlus)return!1;') -or
        $nativeSource.Contains('if(!s&&z(t)&&!a?.fromWotPlus)return!1;') -or
        $nativeSource.Contains('if(!s&&P(t)&&!a?.fromWotPlus)return!1;')
    )) {
        throw 'Native rental filter does not preserve the client selection behavior.'
    }
    $comp7Bundle = $zip.GetEntry($comp7BundlePath)
    $comp7Stream = $comp7Bundle.Open()
    $comp7Reader = New-Object IO.StreamReader($comp7Stream, [Text.Encoding]::UTF8)
    try {
        $comp7Source = $comp7Reader.ReadToEnd()
    }
    finally {
        $comp7Reader.Dispose()
        $comp7Stream.Dispose()
    }
    if (-not (
            $comp7Source.Contains('t+=b)e.push(N.slice(t,t+b))') -or
            $comp7Source.Contains('a+=_)t.push(e.slice(a,a+_))') -or
            $comp7Source.Contains('for(let t=0;t<N.length;t+=2)e.push(N.slice(t,t+2))')
        )) {
        throw 'Comp7 carousel bundle does not contain the configured row chunker.'
    }
    if (-not (
            ($comp7Source.Contains('totalElements:1<b?w.length:C.length') -and
             $comp7Source.Contains('return 1<b?')) -or
            ($comp7Source.Contains('totalElements:1<_?v.length:b.length') -and
             $comp7Source.Contains('return 1<_?'))
        )) {
        throw 'Comp7 carousel bundle does not render more than two rows.'
    }
    if (-not $comp7Source.Contains('3===s&&"hcc-native-carousel-page--3",4===s&&"hcc-native-carousel-page--4"')) {
        throw 'Comp7 carousel page does not expose three- and four-row layout classes.'
    }
    $frontlineBundle = $zip.GetEntry($frontlineBundlePath)
    $frontlineStream = $frontlineBundle.Open()
    $frontlineReader = New-Object IO.StreamReader($frontlineStream, [Text.Encoding]::UTF8)
    try {
        $frontlineSource = $frontlineReader.ReadToEnd()
    }
    finally {
        $frontlineReader.Dispose()
        $frontlineStream.Dispose()
    }
    if (-not $frontlineSource.Contains('for(let a=0;a<e.length;a+=h)t.push(e.slice(a,a+h))') -or
        -not $frontlineSource.Contains('const n=t.at(-1);if(n)for(;n.length<h;)n.push(q_)')) {
        throw 'Frontline carousel bundle does not chunk vehicles according to the configured row count.'
    }
    if (-not $frontlineSource.Contains('totalElements:1<h?x.length:b.length') -or
        -not $frontlineSource.Contains('return 1<h?(0,nr.jsx)(ge,')) {
        throw 'Frontline carousel bundle does not render three- and four-row carousels.'
    }
    if (-not $frontlineSource.Contains('className:Sa(CR,2===s&&jR,3===s&&"hcc-native-carousel-page--3",4===s&&"hcc-native-carousel-page--4")')) {
        throw 'Frontline carousel page does not apply the three- and four-row heights to its layout container.'
    }
    if (-not $frontlineSource.Contains('hccSortJson:r.hccSortJson') -or
        -not $frontlineSource.Contains('hcc.filtered||allowed.has(String(e.id))') -or
        -not $frontlineSource.Contains('hcc.filtered||allowed.has(String(a.id))') -or
        -not $frontlineSource.Contains('values[String(e.id)]')) {
        throw 'Frontline carousel does not apply HCC filtering and sorting to its vehicle list.'
    }
    if (-not $frontlineSource.Contains('JSON.parse(e.requires.filters.model.hccSortJson.get()') -or
        -not $frontlineSource.Contains('hcc.filtered&&i.splice(0,i.length,...i.filter(e=>hccAllowed.has(String(e.id))||hccAllowed.has(String(e.inventoryId))))') -or
        -not $frontlineSource.Contains('return 0}),ls(()=>a.set(i))')) {
        throw 'Frontline rendered carousel list does not apply HCC filtering and sorting, including playlists.'
    }
    $tooltipBundle = $zip.GetEntry($tooltipBundlePath)
    $tooltipStream = $tooltipBundle.Open()
    $tooltipReader = New-Object IO.StreamReader($tooltipStream, [Text.Encoding]::UTF8)
    try {
        $tooltipSource = $tooltipReader.ReadToEnd()
    }
    finally {
        $tooltipReader.Dispose()
        $tooltipStream.Dispose()
    }
    if (-not $tooltipSource.Contains('[mod_hangar_carousel_classic] script loaded')) {
        throw 'Native vehicle tooltip bundle does not contain the Classic renderer.'
    }

    $tooltipCss = $zip.GetEntry('res/gui/gameface/_dist/production/mono/hangar/vehicle_tooltip/vehicle_tooltip.css')
    $tooltipCssStream = $tooltipCss.Open()
    $tooltipCssReader = New-Object IO.StreamReader($tooltipCssStream, [Text.Encoding]::UTF8)
    try {
        $tooltipCssSource = $tooltipCssReader.ReadToEnd()
    }
    finally {
        $tooltipCssReader.Dispose()
        $tooltipCssStream.Dispose()
    }
    if (-not $tooltipCssSource.Contains('.hcc-tooltip-stats-title')) {
        throw 'Native vehicle tooltip stylesheet does not contain the Classic styles.'
    }

    $css = $zip.GetEntry('res/gui/gameface/mods/hcc/hangar_carousel_classic/hangar_carousel_classic.css')
    $cssStream = $css.Open()
    $cssReader = New-Object IO.StreamReader($cssStream, [Text.Encoding]::UTF8)
    try {
        $cssSource = $cssReader.ReadToEnd()
    }
    finally {
        $cssReader.Dispose()
        $cssStream.Dispose()
    }
    if ($cssSource.Contains('calc(')) {
        throw 'Unsupported Gameface calc() expression found.'
    }
    if ($cssSource -match ':not\(' -or $cssSource -match ':disabled') {
        throw 'Unsupported Gameface CSS pseudo-class found (:not/:disabled).'
    }
    foreach ($requiredRule in @(
        '.hcc-native-carousel-page--3 {',
        '.hcc-native-carousel-page--4 {',
        'height: 220rem !important;',
        'height: 291rem !important;',
        'height: 241rem !important;',
        'height: 319rem !important;',
        'height: 274rem !important;',
        'height: 363rem !important;',
        'height: 334rem !important;',
        'height: 443rem !important;'
    )) {
        if (-not $cssSource.Contains($requiredRule)) {
            throw "Native carousel row-height rule is missing: $requiredRule"
        }
    }
    if ($cssSource.Contains('height: auto !important;') -or
        $cssSource.Contains('--card-height:') -or
        $jsSource.Contains('hcc-vehicle-carousel-page--')) {
        throw 'Unsupported carousel auto-height, card-height, or fallback-page rule found.'
    }
    if (-not $cssSource.Contains('[data-test-id="buyTank"]') -or
        -not $cssSource.Contains('.hcc-native-sort-button')) {
        throw 'Action-card visibility or sorting styles are missing.'
    }
    if (-not $cssSource.Contains('.hcc-native-filter svg *') -or
        -not $cssSource.Contains('stroke: #fff !important') -or
        -not $cssSource.Contains('.hcc-native-row-button svg *') -or
        -not $cssSource.Contains('.hcc-native-sort-svg')) {
        throw 'Filter and sorting glyphs are not force-colored white.'
    }
    if ($cssSource.Contains('-webkit-text-fill-color')) {
        throw 'Unsupported Gameface text-fill style found.'
    }
    if ($cssSource.Contains('hcp-currency-lock')) {
        throw 'Currency protection styles must not be included in this classic carousel mod.'
    }
}
finally {
    $zip.Dispose()
}

Write-Output "Validated: $PackagePath"
