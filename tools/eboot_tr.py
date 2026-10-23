"""English text for the EBOOT (menus, config screen, save/load messages) and the relocating patcher.

Usage: eboot_tr.py in.ELF out.ELF
Every catalogued string (ebootcat.py) is rewritten into the space freed by all of them, then
every 32-bit pointer word and lui/addiu pair is repointed. Strings shown by the PSP system
save dialog (PLAIN) are written as plain ASCII; character tables (KEEP) are left untouched.
"""
import sys, os, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = 'Check again?'
Q = '“%s”'

TR = {
    'はい': 'Yes', 'いいえ': 'No', '／': '/',
    '『%T』のファイルが存在しません。\nファイルを作成してもよろしいですか？': 'No %T file exists.\nCreate a new file?',
    '『%T』のファイルが破損しています。\nファイルを上書きしてもよろしいですか？': 'The %T file is corrupted.\nOverwrite the file?',
    '『%T』のファイルのチェックに失敗しました。\nもう一度チェックしますか？': 'Failed to check the %T file.\n' + CHECK,
    '『%T』のファイルのロードに失敗しました。\nもう一度チェックしますか？': 'Failed to load the %T file.\n' + CHECK,
    '『%T』のファイルのセーブに失敗しました。\nもう一度チェックしますか？': 'Failed to save the %T file.\n' + CHECK,
    '『%T』のファイルの新規作成に失敗しました。\nもう一度チェックしますか？': 'Failed to create the %T file.\n' + CHECK,
    '『%T』のファイルが存在しません。\nもう一度チェックしますか？': 'No %T file exists.\n' + CHECK,
    '『%T』のファイルが破損しています。\nもう一度チェックしますか？': 'The %T file is corrupted.\n' + CHECK,
    'このデータで開始しますか？': 'Start with this data?',
    '既にデータが存在します。\n上書きしてよろしいですか？': 'Data already exists.\nOverwrite it?',
    'システムデータをロードしました。': 'System data loaded.',
    'システムデータが存在しません。\nもう一度チェックしますか？': 'No system data exists.\n' + CHECK,
    'システムデータのロードに失敗しました。\nもう一度チェックしますか？': 'Failed to load system data.\n' + CHECK,
    'システムデータが破損しています。\nもう一度チェックしますか？': 'System data is corrupted.\n' + CHECK,
    'もう一度チェックしますか？': CHECK,
    'このデータで開始しますか？\n(※クイックロードのデータは削除されます)': 'Start with this data?\n(Quick load data will be deleted.)',
    'このデータで開始しますか？\n(※これ以降のクイックロードのデータは削除されます)':
        'Start with this data?\n(Any later quick load data will be deleted.)',
    '『%T』のファイルが既に存在しています。\nファイルを上書きしてもよろしいですか？': 'A %T file already exists.\nOverwrite the file?',
    'システムデータをセーブしました。': 'System data saved.',
    'システムデータを作成しました。': 'System data created.',
    'システムデータをセーブしますか？': 'Save system data?',
    'システムデータのチェックに失敗しました。\nもう一度チェックしますか？': 'Failed to check system data.\n' + CHECK,
    '『%s』のセーブデータを探して\n『%T』に反映させますか？': 'Search for %s save data\nand carry it over to %T?',
    '『%s』のセーブデータが存在しません。\nもう一度チェックしますか？': 'No %s save data exists.\n' + CHECK,
    '『%s』のセーブデータが見つかりました。': '%s save data found.',
    'データのロードに失敗しました。\nもう一度チェックしますか？': 'Failed to load data.\n' + CHECK,
    'データが破損しています。\nもう一度チェックしますか？': 'The data is corrupted.\n' + CHECK,
    'データのチェックに失敗しました。\nもう一度チェックしますか？': 'Failed to check data.\n' + CHECK,
    '『%s』のセーブデータを探して\n『%T』に反映させますか？\n（今後、起動時にデータサーチは行いません。\n再度データサーチを行う場合は、タイトル画面の\nＳｙｓｔｅｍからＤａｔａ Ｓｅａｒｃｈを選択してください）':
        'Search for %s save data\nand carry it over to %T?\n(Data will no longer be searched for at startup.\nTo search again, select Data Search\nfrom System on the title screen.)',
    'この場所に戻りますか？': 'Return to this point?',
    'このキャラクターで開始しますか？': 'Start with this character?',
    'このシーンをプレイしますか？': 'Play this scene?',
    '電源をオフにしますか？': 'Turn the power off?',
    '上書きセーブを行わずに、セーブを終了しますか？': 'Exit without overwriting your save?',
    'クリアエンディング数': 'Endings Cleared',
    'ＣＧ Ｇａｌｌｅｒｙ完成度': 'CG Gallery Completion',
    'Ｍｕｓｉｃ Ｇａｌｌｅｒｙ完成度': 'Music Gallery Completion',
    'Ｔｉｐｓ完成度': 'Tips Completion',
    'メッセージ既読率': 'Message Read Rate',
    '総プレイ時間': 'Total Play Time',
    '名前': 'Name', '『%s』': '“%s”', '？？？': '???', '未定義': 'Undefined',
    '日': 'Sun', '月': 'Mon', '火': 'Tue', '水': 'Wed', '木': 'Thu', '金': 'Fri', '土': 'Sat',
    '%d月%d日（%s）': '%d/%d (%s)', '%d月%d日': '%d/%d',
    'Ｓａｖｅ': 'Save', 'Ｌｏａｄ': 'Load', 'Ｑｕｉｃｋ Ｓａｖｅ': 'Quick Save', 'Ｑｕｉｃｋ Ｌｏａｄ': 'Quick Load',
    'Ｔｉｐｓ': 'Tips', 'Ｃｏｎｆｉｇ': 'Config', 'Ｈｅｌｐ': 'Help', 'Ｒｅｔｕｒｎ Ｔｉｔｌｅ': 'Return to Title',
    'Ｅｘｉｔ': 'Exit', 'Ｒｅｓｔａｒｔ': 'Restart',
    'ゲームを終了して、タイトル画面に戻りますか？': 'Quit the game and return to the title screen?',
    'ゲームを終了して、クリアリスト画面に戻りますか？': 'Quit the game and return to the Clear List?',
    '：': ':',
    'シーンタイトル': 'Scene Title', 'トータル既読率': 'Total Read Rate', 'シーン既読率': 'Scene Read Rate',
    '現プレイ時間': 'Current Play Time',
    # config descriptions
    'コントローラのタイプを設定します。タイプ１はＬの季節風%Nの設定、タイプ２は通常ノベルタイプの設定です。%N○ボタンで操作マニュアルが参照できます。':
        'Sets the controller type. Type 1 uses the “L no%NKisetsu” layout; Type 2 is a standard visual novel%Nlayout. Press ○ to view the controls manual.',
    '画面全体の表示位置を調整します。': 'Adjusts the position of the whole screen.',
    'メッセージウィンドウの表示位置を調整します。': 'Adjusts the position of the message window.',
    'メッセージウィンドウのカラーを設定します。': 'Sets the color of the message window.',
    'メッセージウィンドウの不透明度を設定します。': 'Sets the opacity of the message window.',
    'メッセージウィンドウの形状を設定します。': 'Sets the shape of the message window.',
    'メッセージフォントのタイプを設定します。': 'Sets the message font style.',
    'キャラクター音声のボリュームを調整します。': 'Adjusts the volume of character voices.',
    '効果音のボリュームを調整します。': 'Adjusts the sound effect volume.',
    'ＢＧＭのボリュームを調整します。': 'Adjusts the music volume.',
    '操作音のボリュームを調整します。': 'Adjusts the system sound volume.',
    '音の出力方式を設定します。': 'Sets the audio output mode.',
    'キャラクター音声再生の有無を設定します。': 'Turns character voices on or off.',
    '主観者の音声再生の有無を設定します。%N※“有り”を選んだ場合でも、主人公が主観者の場合は%N音声は再生されません。':
        'Turns the voice of the viewpoint character on or off.%NEven when set to “On,” no voice plays while%Nthe protagonist is the viewpoint character.',
    'キャラクター別の音声再生の有無を設定します。': 'Turns voices on or off for each character.',
    '音声再生中にＢＧＭの音量を下げる機能です。%NＢＧＭの音量の下げ幅を設定します。':
        'Lowers the music volume while voices play.%NSets how much the music is lowered.',
    '音声の有るメッセージでの、メッセージウィンドウの表示の有無を設定します。':
        'Shows or hides the message window for voiced lines.',
    '音声とメッセージ表示の同期を設定します。%N“同期する”を選んだ場合、音声有りセリフは音声に同期し、音声無しセリフは固定速度で表示されます。':
        'Syncs text display with voices. When set to “Sync,”%Nvoiced lines follow the voice and unvoiced lines%Nare shown at a fixed speed.',
    'メッセージの表示スピードを調整します。%Nセリフメッセージは“音声とメッセージの同期”の設定が%N優先されます。':
        'Adjusts the text speed. For dialogue, the%N“Voice/Text Sync” setting takes priority.',
    'オートモード時のスピードを調整します。': 'Adjusts the speed of Auto mode.',
    'スキップのスピードを調整します。': 'Adjusts the skip speed.',
    'スキップ(STARTボタンでのスキップ)のモードを%N設定します。': 'Sets the skip mode%N(skipping with the START button).',
    '妄想トリガー出現時にスキップを停止するかを%N設定します。': 'Sets whether skipping stops%Nwhen a delusion trigger appears.',
    'スキップ時のキャラクター表示のタイプを設定します。%N“シルエット”を選んだ場合、キャラクターの読み込みが軽減されスキップ速度が速くなります。':
        'Sets how characters are shown while skipping.%N“Silhouette” reduces character loading and%Nmakes skipping faster.',
    'スキップ時の表情ウィンドウ表示を設定します。%N“表示無し”を選んだ場合、キャラクターの読み込みが軽減されスキップ速度が速くなります。':
        'Sets the expression window display while skipping.%N“Off” reduces character loading and%Nmakes skipping faster.',
    'スキップ時のスクロール演出方法を設定します。%N“演出カット”を選んだ場合、スクロール等の演出が省かれスキップが少し速くなります。':
        'Sets scrolling effects while skipping.%N“Cut Effects” omits scrolling and similar effects,%Nmaking skipping slightly faster.',
    'ゲーム開始時のメッセージ送りを設定します。%Nゲーム開始時、ロード時、メッセージログジャンプ時に%N設定した状態で開始されます。':
        'Sets how text advances when the game starts.%NApplies when starting, loading, or jumping%Nfrom the message log.',
    '選択肢で、既読選択肢のカラーを変更するか、設定します。': 'Sets whether already-chosen options are recolored.',
    'メッセージログで、既読メッセージのカラーを変更するか、設定します。': 'Sets whether read messages are recolored in the log.',
    '自動クイックセーブのポイントを設定します。%N“タイトル毎”は各章の開始時、“選択肢毎”は妄想トリガー及び、YES/NO選択出現時にクイックセーブが行われます。':
        'Sets when the game quick saves. “Each Title” saves%Nat the start of each chapter; “Each Choice” saves%Nat delusion triggers and YES/NO choices.',
    'シーン変更時のシーンタイトル表示の有無を設定します。': 'Shows or hides the scene title on scene changes.',
    '日付表示の有無を設定します。': 'Shows or hides the date.',
    '場所表示の有無を設定します。': 'Shows or hides the location.',
    '名前の表示方式を設定します。': 'Sets how names are displayed.',
    'メッセージアイコンのタイプを設定します。': 'Sets the message icon type.',
    '主人公のキャラクタービジュアル表示の有無を設定します。': 'Shows or hides the protagonist’s portrait.',
    '主観者変更時の演出方法を設定します。': 'Sets the effect used when the viewpoint changes.',
    'シミュレーション画面(ステータスウィンドウ、ビジュアルウィンドウ)でのボタン入力待ちの有無を設定します。':
        'Sets whether simulation screens (status and%Nvisual windows) wait for a button press.',
    'ステータスウィンドウで“好感度”表示の有無を設定します。': 'Shows or hides “Affection” in the status window.',
    'ステータスウィンドウで“隠しパラメータ”表示の有無を設定します。': 'Shows or hides “Hidden Parameters”%Nin the status window.',
    'ステータスウィンドウでのパラメータの表示方法を設定します。': 'Sets how parameters are shown%Nin the status window.',
    'シーン別既読率、トータル既読率を%N画面右上にリアルタイムに表示します。':
        'Shows the scene and total read rates%Nin the upper right of the screen.',
    'ＳＥのタイプを設定します。': 'Sets the sound effect type.',
    'キャラの服装を設定します。': 'Sets the characters’ outfits.',
    'コントローラの“振動”の有無を設定します。': 'Turns controller vibration on or off.',
    '未使用': 'Unused',
    'コンフィグを初期設定に戻します。': 'Restores all settings to their defaults.',
    'コンフィグ設定を終了します。': 'Exits the settings.',
    '%sの音声の有無を設定します。': 'Turns %s’s voice on or off.',
    'ページ内のコンフィグを初期設定に戻します。': 'Restores this page’s settings to their defaults.',
    '前ページに戻ります。': 'Returns to the previous page.',
    # config item names
    'コントローラのタイプ': 'Controller Type', '画面の表示位置': 'Screen Position', 'ウィンドウの表示位置': 'Window Position',
    'ウィンドウのカラー': 'Window Color', 'ウィンドウの濃さ': 'Window Opacity', 'ウィンドウの形状': 'Window Shape',
    'フォントのタイプ': 'Font Style', '音声のボリューム': 'Voice Volume', '効果音のボリューム': 'SFX Volume',
    'ＢＧＭのボリューム': 'Music Volume', '操作音のボリューム': 'System Volume', '音の出力': 'Audio Output',
    '音声再生': 'Voices', '主観者の音声再生': 'Viewpoint Voice', 'キャラクター別の音声再生': 'Voices by Character',
    '音声ハイライト': 'Voice Ducking', '音声有りメッセージの表示': 'Window on Voiced Lines',
    '音声とメッセージの同期': 'Voice/Text Sync', 'メッセージの表示スピード': 'Text Speed',
    'オートモードのスピード': 'Auto Mode Speed', 'スキップのスピード': 'Skip Speed', 'スキップのモード': 'Skip Mode',
    '妄想トリガーでのスキップ': 'Skip at Delusion Triggers', 'スキップ時のキャラクター': 'Characters While Skipping',
    'スキップ時の表情ウィンドウ': 'Expressions While Skipping', 'スキップ時のスクロール演出': 'Scrolling While Skipping',
    'ゲーム開始時の状態': 'Mode at Start', '選択肢の既読色の有無': 'Chosen Option Color',
    '読み返しの既読色の有無': 'Read Text Color', '自動クイックセーブの設定': 'Auto Quick Save',
    'シーンタイトルの表示': 'Scene Title Display', '日付の表示': 'Date Display', '場所の表示': 'Location Display',
    '名前の表示': 'Name Display', 'メッセージアイコンのタイプ': 'Message Icon', '主人公の表示': 'Protagonist Portrait',
    '主観者変更時の演出': 'Viewpoint Change Effect', 'シミュレーションでの一時停止': 'Pause in Simulations',
    '好感度の表示': 'Show Affection', '隠しパラメータの表示': 'Show Hidden Parameters', 'パラメータの表示方': 'Parameter Display',
    '既読率の表示': 'Show Read Rate', 'ＳＥのタイプ': 'SFX Type', 'コスチューム': 'Costume', '振動機能': 'Vibration',
    '初期設定に戻す': 'Restore Defaults', '戻る': 'Back', '%sの音声': '%s’s Voice',
    # config values
    'タイプ１（標準）': 'Type 1 (Default)', 'タイプ２': 'Type 2', 'Ｘ ： ': 'X: ', 'Ｙ ： ': 'Y: ',
    'オリジナル': 'Original', '表情ウィンドウ無し': 'No Expressions', 'キッド標準': 'KID Default',
    '影無し': 'No Shadow', '影有り': 'Shadow', '縁有り': 'Outline',
    '１（小さい）': '1 (Small)', '２': '2', '３': '3', '４': '4', '５': '5', '６（大きい）': '6 (Large)',
    'ステレオ': 'Stereo', 'モノラル': 'Mono', '有り': 'On', '無し': 'Off', '小': 'Low', '中': 'Mid', '大': 'High',
    '表示する': 'Show', '表示しない': 'Hide', '同期する': 'Sync', '同期しない': 'Don’t Sync',
    '標準（推奨）': 'Default (Rec.)', '紅絹（声）': 'Momi (Voice)', '加絵（声）': 'Kae (Voice)',
    '最遅': 'Slowest', '遅い': 'Slow', '普通': 'Normal', '速い': 'Fast', '最速': 'Fastest', '一括表示': 'Instant',
    '既読文章のみ': 'Read Text Only', '全ての文章': 'All Text', '未読時はオート': 'Auto When Unread',
    '停止する': 'Stop', '停止しない': 'Don’t Stop', '標準': 'Default', 'シルエット（高速）': 'Silhouette (Fast)',
    '表示有り': 'On', '表示無し（高速）': 'Off (Fast)', '演出カット（高速）': 'Cut Effects (Fast)',
    '通常': 'Normal', 'オート': 'Auto', 'スキップ': 'Skip', '既読色有り': 'Color On', '既読色無し': 'Color Off',
    'しない': 'Off', '選択肢毎': 'Each Choice', 'タイトル毎': 'Each Title', '選択肢＋タイトル毎': 'Choice + Title',
    '文字表示': 'Text', 'アイコン表示': 'Icon', 'キャラＡ': 'Character A', 'キャラＢ': 'Character B',
    '通常表示': 'Normal', '簡易表示': 'Simple', '自動進行': 'Auto Advance', '数値表示': 'Numbers', '特殊表示': 'Special',
    '振動する': 'On', '振動しない': 'Off', 'い': '', 'ない': '',
    '±%02d': '±%02d', '－%02d': '-%02d', '＋%02d': '+%02d',
    'Ｓｕｎ': 'Sun', 'Ｍｏｎ': 'Mon', 'Ｔｕｅ': 'Tue', 'Ｗｅｄ': 'Wed', 'Ｔｈｕ': 'Thu', 'Ｆｒｉ': 'Fri', 'Ｓａｔ': 'Sat',
    '【%s】': '[%s]',
    # PSP save dialog / save list (system font)
    '今日': 'Today', '昨日': 'Yesterday', 'Ｎｏ Ｄａｔａ': 'No Data', 'データが壊れています': 'Corrupted data',
    '%sが見つかりません': '%s not found', '手動クイックセーブ': 'Manual Quick Save', 'Ｌａｓｔ Ｇａｍｅ': 'Last Game',
    'データのチェック中です。\nメモリースティック㌻を抜いたり、\n本体の電源を切ったりしないで下さい。':
        'Checking data.\nDo not remove the Memory Stick™\nor turn off the power.',
    'データのロード中です。\nメモリースティック㌻を抜いたり、\n本体の電源を切ったりしないで下さい。':
        'Loading data.\nDo not remove the Memory Stick™\nor turn off the power.',
    'データのセーブ中です。\nメモリースティック㌻を抜いたり、\n本体の電源を切ったりしないで下さい。':
        'Saving data.\nDo not remove the Memory Stick™\nor turn off the power.',
    'メモリースティック㌻が入っていません。\nデータをセーブするには%savesize%KBの空き容量が必要です。':
        'No Memory Stick™ is inserted.\n%savesize% KB of free space is required to save.',
    'データが見つかりません。\nメモリースティック㌻の空き容量が不足しています。\nデータをセーブするには%savesize%KBの空き容量が必要です。':
        'No data found.\nThere is not enough free space on the Memory Stick™.\n%savesize% KB of free space is required to save.',
    'データが見つかりません。': 'No data found.', 'データが破損しています。': 'The data is corrupted.',
    'データのロードに失敗しました。': 'Failed to load data.', 'データのセーブに失敗しました。': 'Failed to save data.',
    '書き込み保護されているため、\nデータのセーブに失敗しました。': 'The Memory Stick™ is write-protected.\nFailed to save data.',
    'データが既に存在しています。\n上書きしてもよろしいですか？': 'Data already exists.\nOverwrite it?',
    'データのチェックを中止しますか？': 'Stop checking data?', 'データのロードを中止しますか？': 'Stop loading data?',
    'データのセーブを中止しますか？': 'Stop saving data?', 'このままゲームを開始しますか？': 'Start the game without saving?',
    '上書きしてもよろしいですか？': 'Overwrite this data?',
    'このまま続けますか？\n（※セーブ時にデータは上書きされます）': 'Continue anyway?\n(Data will be overwritten when you save.)',
    '不要なデータを削除しますか？': 'Delete unneeded data?',
    '　プレイ時間：%3d時間%02d分': ' Play Time: %3dh %02dm',
}

# left exactly as they are (character tables, masks, rules)
KEEP_PREFIX = ('０１２３４５６７８９', '？？？？', '「『（', '“「『（', '”」』）', '　　　', '───', '――――')
# shown by the PSP system save dialog/list: plain ASCII
PLAIN_FROM = 0x10c85c
# unit characters drawn one by one after numbers: keep 4 chars x 2 bytes
WIDE2 = {'時間分秒': 'hrms'}
# PS2-only leftovers (memory card, disc swap, progressive scan): never shown on PSP
PS2_ONLY = ('メモリーカード', 'ディスク', 'プログレッシブ')


def plain(t):
    return (t.replace('’', "'").replace('“', '"').replace('”', '"').replace('™', '(TM)')
            .encode('ascii', 'replace'))


def encode(item):
    t = item['text']
    if any(t.startswith(k) for k in KEEP_PREFIX):
        return None
    if t in WIDE2:
        m = enc._load()
        return b''.join(bytes.fromhex(m['regular'][c]) for c in WIDE2[t])
    if any(k in t for k in PS2_ONLY):
        return b''
    if t not in TR:
        raise KeyError('no translation for %r' % t)
    e = TR[t]
    if item['off'] >= PLAIN_FROM:
        return plain(e)
    return enc.encode(e.replace('\n', '%N') if False else e)


def main(src, dst):
    import ebootrefs as E
    B = bytearray(open(src, 'rb').read())
    items = json.load(open(os.path.join(ROOT, 'work', 'eboot', 'catalog.json'), encoding='utf-8'))
    new = []
    free = []
    for it in items:
        nb = encode(it)
        if nb is None:
            continue
        new.append((it, nb + b'\0'))
        free.append([it['off'], it['off'] + it['slot']])
    # merge free segments, clear them
    free.sort()
    segs = []
    for a, b in free:
        if segs and a <= segs[-1][1]:
            segs[-1][1] = max(segs[-1][1], b)
        else:
            segs.append([a, b])
    for a, b in segs:
        B[a:b] = bytes(b - a)
    # place longest first, identical strings shared
    placed = {}
    new.sort(key=lambda x: -len(x[1]))
    for it, nb in new:
        if nb in placed:
            it['new'] = placed[nb]; continue
        for s in segs:
            a = (s[0] + 3) & ~3 if len(nb) > 4 else s[0]
            if a + len(nb) <= s[1]:
                B[a:a + len(nb)] = nb
                if a == s[0]:
                    s[0] = a + len(nb)
                else:
                    segs.append([a + len(nb), s[1]]); s[1] = a
                it['new'] = placed[nb] = a
                break
        else:
            raise ValueError('EBOOT string pool full (%d bytes left); string %r' %
                             (sum(b - a for a, b in segs), it['text']))
    # repoint
    for it, nb in new:
        v = E.va(it['new'])
        for w in it['words']:
            struct.pack_into('<I', B, w, v)
        for lui_p, lo_p in it['code']:
            hi = (v + 0x8000) >> 16; lo = v & 0xFFFF
            wl = struct.unpack_from('<I', B, lui_p)[0]
            wa = struct.unpack_from('<I', B, lo_p)[0]
            if (wa >> 26) == 0x0D:     # ori: unsigned low half
                hi = v >> 16
            struct.pack_into('<I', B, lui_p, (wl & 0xFFFF0000) | hi)
            struct.pack_into('<I', B, lo_p, (wa & 0xFFFF0000) | lo)
    import ebootfix
    ebootfix.apply(B)                  # code fixes (glyph-cache underline)
    open(dst, 'wb').write(B)
    print('EBOOT strings rewritten:', len(new), 'pool left:', sum(b - a for a, b in segs), 'bytes')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
