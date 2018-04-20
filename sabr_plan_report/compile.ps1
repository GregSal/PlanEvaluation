pyinstaller --noconfirm --log-level=WARN '
    --onedir --nowindow '
    --add-data="DVH.png;." '
    --add-data=".\Data\Alias List.txt;Data" '
    --add-data=".\Data\Report Reference 48 in 4.txt;Data" '
    --add-data=".\Data\Report Reference 60 in 8.txt;Data" '
    --add-data=".\Data\SABR  Plan Evaluation Worksheet BLANK.xls;Data" '
    --icon=.\DVH.ico '
    build_SABR_plan_report.py
