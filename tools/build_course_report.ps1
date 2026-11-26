param([string]$WorkspaceRoot = (Split-Path $PSScriptRoot -Parent))
$ErrorActionPreference = 'Stop'
$reportDirectory = Join-Path $WorkspaceRoot 'reports'
$sourcePath = Join-Path $reportDirectory 'course_report.html'
[string]$docxPath = Join-Path $reportDirectory 'Group6_FandomFaultLines_Report.docx'
[string]$pdfPath = Join-Path $reportDirectory 'Group6_FandomFaultLines_Report.pdf'
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $word.Options.SaveNormalPrompt = $false
    $document = $word.Documents.Open($sourcePath, $false, $true, $false)
    Write-Output 'Opened report source'
    $document.PageSetup.PageWidth = 595.3
    $document.PageSetup.PageHeight = 841.9
    $document.PageSetup.TopMargin = 48
    $document.PageSetup.BottomMargin = 48
    $document.PageSetup.LeftMargin = 50
    $document.PageSetup.RightMargin = 50
    $document.PageSetup.FooterDistance = 22
    Write-Output ('Formatting ' + $document.Tables.Count + ' tables')
    for ($tableIndex = 1; $tableIndex -le $document.Tables.Count; $tableIndex++) {
        $table = $document.Tables.Item($tableIndex)
        $table.Rows.AllowBreakAcrossPages = 0
        $table.Rows.Item(1).HeadingFormat = -1
        $table.TopPadding = 4
        $table.BottomPadding = 4
        $table.LeftPadding = 5
        $table.RightPadding = 5
        $table.Range.ParagraphFormat.SpaceBefore = 0
        $table.Range.ParagraphFormat.SpaceAfter = 0
        $table.Range.ParagraphFormat.LineSpacingRule = 0
        $table.Range.Cells.VerticalAlignment = 1
        for ($rowIndex = 2; $rowIndex -le $table.Rows.Count; $rowIndex++) {
            $row = $table.Rows.Item($rowIndex)
            $row.Shading.BackgroundPatternColor = $(if ($rowIndex % 2 -eq 0) { 16250353 } else { 16777215 })
        }
    }
    Write-Output ('Embedding ' + $document.InlineShapes.Count + ' images')
    Add-Type -AssemblyName System.Drawing
    $imageTags = [regex]::Matches((Get-Content -LiteralPath $sourcePath -Raw), '<img src="([^"]+)" width="([0-9]+)"')
    if ($imageTags.Count -ne $document.InlineShapes.Count) { throw 'Image source mismatch' }
    for ($imageIndex = $document.InlineShapes.Count; $imageIndex -ge 1; $imageIndex--) {
        $shape = $document.InlineShapes.Item($imageIndex)
        $imageTag = $imageTags.Item($imageIndex - 1)
        $imagePath = [IO.Path]::GetFullPath((Join-Path $reportDirectory $imageTag.Groups.Item(1).Value))
        $bitmap = [Drawing.Image]::FromFile($imagePath)
        try {
            $figureWidth = [double]$imageTag.Groups.Item(2).Value * 0.75
            $shape.LockAspectRatio = 0
            $shape.Width = $figureWidth
            $shape.Height = $figureWidth * $bitmap.Height / $bitmap.Width
        } finally { $bitmap.Dispose() }
        if ($shape.Type -eq 4) { $shape.LinkFormat.SavePictureWithDocument = $true; $shape.LinkFormat.BreakLink() }
    }
    Write-Output 'Adding footer'
    $footer = $document.Sections.Item(1).Footers.Item(1).Range
    $footer.Text = 'Group 6 | Computational Social Media Analysis                       '
    $footer.Font.Name = 'Calibri'
    $footer.Font.Size = 9
    $footer.Font.Color = 0
    $footer.ParagraphFormat.Alignment = 2
    $end = $footer.Duplicate
    $end.Collapse(0)
    [void]$document.Fields.Add($end, 33)
    Write-Output 'Paginating report'
    $document.Repaginate()
    [void]$document.Fields.Update()
    Write-Output 'Saving DOCX'
    $docxFormat = 16
    $document.SaveAs([ref]$docxPath, [ref]$docxFormat)
    Write-Output 'Exporting PDF'
    $document.ExportAsFixedFormat($pdfPath, 17)
    Write-Output ('Saved DOCX and PDF; pages=' + $document.ComputeStatistics(2))
    Write-Output ('Inline images=' + $document.InlineShapes.Count + '; tables=' + $document.Tables.Count)
} finally {
    if ($null -ne $document) { $document.Close(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($document) }
    if ($null -ne $word) { $word.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.IO.Compression
$archive = [IO.Compression.ZipFile]::Open($docxPath, [IO.Compression.ZipArchiveMode]::Update)
try {
    $entry = $archive.GetEntry('docProps/core.xml')
    $reader = New-Object IO.StreamReader($entry.Open())
    [xml]$core = $reader.ReadToEnd()
    $reader.Dispose()
    $ns = New-Object Xml.XmlNamespaceManager($core.NameTable)
    $ns.AddNamespace('dc', 'http://purl.org/dc/elements/1.1/')
    $ns.AddNamespace('cp', 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties')
    $core.SelectSingleNode('//dc:creator', $ns).InnerText = 'Mayank Gupta; Anurag Kumar; Jhalak Kapila'
    $core.SelectSingleNode('//cp:lastModifiedBy', $ns).InnerText = 'Group 6'
    $entry.Delete()
    $replacement = $archive.CreateEntry('docProps/core.xml')
    $writer = New-Object IO.StreamWriter($replacement.Open(), (New-Object Text.UTF8Encoding($false)))
    $writer.Write($core.OuterXml)
    $writer.Dispose()
} finally { $archive.Dispose() }
