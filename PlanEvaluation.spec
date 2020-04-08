# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['PlanEvaluation.py'],
             pathex=["C:\\Users\\gsalomon\\OneDrive - Queen's University\\Python\\Projects\\EclipseRelated\\PlanEvaluation"],
             binaries=[],
             datas=[('.\\Data', 'Data'), ('.\\DVH Files', 'DVH Files'), ('.\\Icons', 'Icons'), ('.\\Output', 'Output'), ('PlanEvaluationConfig.xml', '.')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='PlanEvaluation',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False , manifest="C:\\Users\\gsalomon\\OneDrive - Queen's University\\Python\\Projects\\EclipseRelated\\PlanEvaluation\\build\\PlanEvaluation\\PlanEvaluation.exe.manifest")
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='PlanEvaluation')
