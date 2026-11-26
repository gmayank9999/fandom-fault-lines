param([string]$WorkspaceRoot = (Split-Path $PSScriptRoot -Parent))
$ErrorActionPreference = 'Stop'
$contentPath = Join-Path $WorkspaceRoot 'reports/presentation/presentation_content.json'
$content = Get-Content -LiteralPath $contentPath -Raw -Encoding UTF8 | ConvertFrom-Json
$outputPath = Join-Path $WorkspaceRoot 'reports/presentation/Group6_FandomFaultLines_Presentation.pptx'
$qaPath = Join-Path $WorkspaceRoot 'logs/presentation_qa'
[void](New-Item -ItemType Directory -Path $qaPath -Force)
Add-Type -AssemblyName System.Drawing

function ColorValue([string]$hex) {
    $red = [Convert]::ToInt32($hex.Substring(0,2),16)
    $green = [Convert]::ToInt32($hex.Substring(2,2),16)
    $blue = [Convert]::ToInt32($hex.Substring(4,2),16)
    return $red + 256*$green + 65536*$blue
}

function AddText($slide, [string]$value, [double]$x, [double]$y, [double]$w, [double]$h,
                 [double]$size=21, [string]$color='173449', [bool]$bold=$false, [string]$align='left') {
    $box = $slide.Shapes.AddTextbox(1,$x,$y,$w,$h)
    $frame = $box.TextFrame
    $frame.MarginLeft = 0; $frame.MarginRight = 0; $frame.MarginTop = 0; $frame.MarginBottom = 0
    $frame.WordWrap = -1; $frame.AutoSize = 0
    $range = $frame.TextRange
    $range.Text = $value
    $range.Font.Name = 'Calibri'; $range.Font.Size = $size
    $range.Font.Bold = $(if($bold) { -1 } else { 0 })
    $range.Font.Color.RGB = ColorValue $color
    $range.ParagraphFormat.SpaceBefore = 0; $range.ParagraphFormat.SpaceAfter = 0
    $range.ParagraphFormat.SpaceWithin = 1.05
    $range.ParagraphFormat.Alignment = $(if($align -eq 'center') {2} else {1})
    # PowerPoint can shrink a newly added empty text box before AutoSize is disabled.
    $box.Width = [single]$w
    $box.Height = [single]$h
    return $box
}

$ppt = $null; $deck = $null
$checks = New-Object System.Collections.Generic.List[object]
try {
    $ppt = New-Object -ComObject PowerPoint.Application
    $deck = $ppt.Presentations.Add(0)
    $deck.PageSetup.SlideWidth = 960; $deck.PageSetup.SlideHeight = 540
    for ($i=0; $i -lt $content.slides.Count; $i++) {
        $spec = $content.slides[$i]
        $slide = $deck.Slides.Add($i+1,12)
        $slide.FollowMasterBackground = 0
        $slide.Background.Fill.Solid(); $slide.Background.Fill.ForeColor.RGB = ColorValue 'FFFFFF'
        if (-not $spec.cover) {
            [void](AddText $slide $spec.title 48 36 864 78 32 '173449' $true)
        }
        foreach ($element in $spec.elements) {
            switch ($element.type) {
                'text' {
                    [void](AddText $slide $element.text $element.x $element.y $element.w $element.h $element.size $element.color $element.bold $element.align)
                }
                'line' {
                    $shape = $slide.Shapes.AddLine($element.x,$element.y,$element.x2,$element.y2)
                    $shape.Line.ForeColor.RGB = ColorValue $element.color
                    $shape.Line.Weight = [single]$element.width
                    if ($element.arrow) { $shape.Line.EndArrowheadStyle = 3 }
                }
                {$_ -in 'rect','ellipse'} {
                    $kind = $(if ($element.type -eq 'ellipse') {9} else {1})
                    $shape = $slide.Shapes.AddShape($kind,$element.x,$element.y,$element.w,$element.h)
                    $shape.Fill.Solid(); $shape.Fill.ForeColor.RGB = ColorValue $element.color
                    $shape.Line.Visible = 0
                }
                'image' {
                    $path = [IO.Path]::GetFullPath((Join-Path $WorkspaceRoot $element.path))
                    $bitmap = [Drawing.Image]::FromFile($path)
                    try {
                        $scale = [Math]::Min($element.w/$bitmap.Width,$element.h/$bitmap.Height)
                        $width = $bitmap.Width*$scale; $height = $bitmap.Height*$scale
                        [void]$slide.Shapes.AddPicture($path,0,-1,
                            ($element.x+($element.w-$width)/2),($element.y+($element.h-$height)/2),$width,$height)
                    } finally { $bitmap.Dispose() }
                }
                'table' {
                    $rowCount = $element.rows.Count+1
                    $colCount = $element.headers.Count
                    $shape = $slide.Shapes.AddTable($rowCount,$colCount,$element.x,$element.y,$element.w,$element.h)
                    $table = $shape.Table
                    for ($c=1; $c -le $colCount; $c++) { $table.Columns.Item($c).Width = $element.widths[$c-1] }
                    for ($r=1; $r -le $rowCount; $r++) {
                        for ($c=1; $c -le $colCount; $c++) {
                            $cell = $table.Cell($r,$c)
                            $frame = $cell.Shape.TextFrame
                            $frame.MarginLeft=10; $frame.MarginRight=10; $frame.MarginTop=7; $frame.MarginBottom=7
                            $frame.VerticalAnchor=3
                            $range=$frame.TextRange
                            $range.Text=$(if($r -eq 1) {$element.headers[$c-1]} else {$element.rows[$r-2][$c-1]})
                            $range.Font.Name='Calibri'; $range.Font.Size=$element.size
                            $range.Font.Bold=$(if($r -eq 1){-1}else{0})
                            $range.Font.Color.RGB=ColorValue $(if($r -eq 1){'FFFFFF'}else{'173449'})
                            $range.ParagraphFormat.SpaceWithin=1
                            $range.ParagraphFormat.SpaceBefore=0; $range.ParagraphFormat.SpaceAfter=0
                            $cell.Shape.Fill.ForeColor.RGB=ColorValue $(if($r -eq 1){'173449'}elseif($r%2 -eq 0){'F0F4F7'}else{'FFFFFF'})
                            for ($b=1;$b -le 4;$b++) {
                                $cell.Borders.Item($b).ForeColor.RGB=ColorValue 'D6DFE5'
                                $cell.Borders.Item($b).Weight=.6
                            }
                        }
                    }
                }
            }
        }
        [void](AddText $slide ([string]($i+1)) 878 518 34 15 11 '76838C' $false 'center')
        $notes = $spec.notes + "`r`n`r`nSources`r`n" + $spec.source
        $slide.NotesPage.Shapes.Placeholders.Item(2).TextFrame.TextRange.Text = $notes
        for ($j=1;$j -le $slide.Shapes.Count;$j++) {
            $shape=$slide.Shapes.Item($j)
            if ($shape.HasTextFrame -eq -1 -and $shape.TextFrame.HasText -eq -1) {
                $used=$shape.TextFrame.TextRange.BoundHeight
                if ($used -gt $shape.Height+2) {
                    $checks.Add([pscustomobject]@{slide=$i+1; shape=$j; text=$shape.TextFrame.TextRange.Text; usedHeight=$used; boxHeight=$shape.Height})
                }
            }
        }
        if (($i+1)%5 -eq 0) { Write-Output ('Built ' + ($i+1) + ' slides') }
    }
    $deck.SaveAs([string]$outputPath,24)
    Write-Output 'Saved editable PowerPoint'
    for ($i=1;$i -le $deck.Slides.Count;$i++) {
        $file = Join-Path $qaPath ('slide-{0:D2}.png' -f $i)
        $deck.Slides.Item($i).Export($file,'PNG',1600,900)
    }
    $deck.SaveAs((Join-Path $qaPath 'presentation.pdf'),32)
    ConvertTo-Json -InputObject @($checks.ToArray()) -Depth 6 | Set-Content -LiteralPath (Join-Path $qaPath 'text_fit.json') -Encoding UTF8
    Write-Output ('Rendered ' + $deck.Slides.Count + ' slides; possible text overflows: ' + $checks.Count)
} finally {
    if ($null -ne $deck) { $deck.Close(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck) }
    if ($null -ne $ppt) {
        if ($ppt.Presentations.Count -eq 0) { $ppt.Quit() }
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($ppt)
    }
}
