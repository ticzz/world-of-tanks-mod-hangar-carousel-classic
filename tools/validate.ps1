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
    $required = @(
        'meta.xml',
        'res/scripts/client/gui/mods/mod_hangar_carousel_classic.pyc',
        'res/gui/gameface/mods/hcc/hangar_carousel_classic/hangar_carousel_classic.js',
        'res/gui/gameface/mods/hcc/hangar_carousel_classic/hangar_carousel_classic.css',
        'res/gui/gameface/mods/hcc/hangar_carousel_classic/hangar_carousel_classic.tooltip.js',
        'res/gui/gameface/mods/hcc/hangar_carousel_classic/hangar_carousel_classic.tooltip.css',
        'res/gui/gameface/_dist/production/mono/hangar/views/main/main.html/bundle.js',
        'res/gui/gameface/_dist/production/mono/hangar/views/vehicle_tooltip/vehicle_tooltip.html/bundle.js',
        'res/gui/gameface/_dist/production/mono/hangar/vehicle_tooltip/vehicle_tooltip.css'
    )
    $names = @($zip.Entries | ForEach-Object FullName)
    foreach ($entry in $required) {
        if ($entry -notin $names) {
            throw "Required package entry is missing: $entry"
        }
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

    $nativeBundle = $zip.GetEntry('res/gui/gameface/_dist/production/mono/hangar/views/main/main.html/bundle.js')
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
            $nativeSource.Contains('t+=i)e.push(j.slice(t,t+i))')
        )) {
        throw 'Native carousel bundle does not contain the generic row chunker.'
    }
    if ($nativeSource.Contains('totalElements:2===v?N.length:w.length')) {
        throw 'Native carousel bundle still contains the two-row-only renderer.'
    }
    if (-not (
            $nativeSource.Contains('3===s&&"hcc-native-carousel--3",4===s&&"hcc-native-carousel--4"') -or
            $nativeSource.Contains('3===v&&"hcc-native-carousel--3",4===v&&"hcc-native-carousel--4"')
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

    $tooltipBundle = $zip.GetEntry('res/gui/gameface/_dist/production/mono/hangar/views/vehicle_tooltip/vehicle_tooltip.html/bundle.js')
    $tooltipStream = $tooltipBundle.Open()
    $tooltipReader = New-Object IO.StreamReader($tooltipStream, [Text.Encoding]::UTF8)
    try {
        $tooltipSource = $tooltipReader.ReadToEnd()
    }
    finally {
        $tooltipReader.Dispose()
        $tooltipStream.Dispose()
    }
    if (-not $tooltipSource.Contains('[HangarCarouselClassicTooltip] script loaded')) {
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
    if (-not $cssSource.Contains('.hcc-native-carousel--3') -or
        -not $cssSource.Contains('.hcc-native-carousel--4') -or
        -not $cssSource.Contains('min-height: 285rem')) {
        throw 'Extended carousel height rules are missing.'
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
