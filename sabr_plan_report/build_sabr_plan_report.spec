# -*- mode: python -*-

block_cipher = None


a = Analysis(['build_SABR_plan_report.py'],
             pathex=['C:\\Users\\gsalomon\\OneDrive for Business 1\\Python\\Projects\\PlanEvaluation\\sabr_plan_report'],
             binaries=[],
             datas=[('DVH.png', '.'), ('DVH.ico', '.'), ('.\\Data', 'Data')],
             hiddenimports=['scipy._lib.messagestream'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='build_SABR_plan_report',
          debug=False,
          strip=False,
          upx=True,
          console=False , icon='DVH.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='build_SABR_plan_report')
