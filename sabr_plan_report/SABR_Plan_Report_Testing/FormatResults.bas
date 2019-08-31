Attribute VB_Name = "Module1"
Sub FormatResults()
Attribute FormatResults.VB_Description = "Format SABR Plan Report Test Results"
Attribute FormatResults.VB_ProcData.VB_Invoke_Func = "g\n14"
'
' Macro1 Macro
'
' Keyboard Shortcut: Ctrl+g
'
    ActiveCell.Columns("A:A").EntireColumn.Select
    With Selection.Interior
        .Pattern = xlSolid
        .PatternColorIndex = xlAutomatic
        .Color = 12611584
        .TintAndShade = 0
        .PatternTintAndShade = 0
    End With
    Selection.ColumnWidth = 1
    ActiveCell.Offset(0, 1).Columns("A:A").EntireColumn.Select
    Selection.Delete Shift:=xlToLeft
    Selection.Delete Shift:=xlToLeft
    Selection.Delete Shift:=xlToLeft
    ActiveCell.Offset(0, 5).Range("A1").Select
End Sub

Sub DeleteColumn()
Attribute DeleteColumn.VB_ProcData.VB_Invoke_Func = "h\n14"
'
' DeleteColumn Macro
' Remove label columns
'
' Keyboard Shortcut: Ctrl+h
'
    Selection.EntireColumn.Delete
    ActiveCell.Offset(0, 1).Range("A1").Select
    Selection.EntireColumn.Delete
    ActiveCell.Offset(0, 3).Range("A1").Select
End Sub

