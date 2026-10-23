"""Shared English UI glossary (CoZ CHAOS;HEAD NOAH terminology) for PSP system files and the EBOOT."""
import re

CHAPTER_TITLES = {
    'Ｅｙｅｓ ｉｎ ｅｙｅｓ': 'Eyes in Eyes', 'Ｃｌｉｃｋ ｍｅ': 'Click Me', '将軍': 'Shogun',
    'Ｄｉ-Ｓｗｏｒｄ': 'DI-sword', '妄想': 'Delusion', 'Ｎｏａｈ': 'Noah', 'ｐｓｙｃｈｏｐａｔｈ': 'Psychopath',
    'Ｉｒ２': 'Ir2', 'ｇｉｇａ-ｌｏ-ｍａｎｉａｃ': 'Gigalomaniac', 'ｂｌｕｅ ｓｋｙ': 'Blue Sky',
    'ｓｉｌｅｎｔ ｓｋｙ': 'Silent Sky', 'ｃｒｙｉｎｇ ｓｋｙ': 'Crying Sky',
    'アニマの像': 'The Anima Image', 'ｄａｙｄｒｅａｍ': 'Daydream', '月と太陽': 'Sun and Moon',
    '罪過に契約の血を': 'A Contract of Blood to Seal Our Sin', 'デウス・エクス・マキナ': 'Deus Ex Machina',
    '殺戮に至る病': 'The Sickness unto Slaughter',
}
ROUTES = {'梨深編': 'Rimi Route', '七海編': 'Nanami Route', '優愛編': 'Yua Route', 'あやせ編': 'Ayase Route',
          'セナ編': 'Sena Route', '梢編': 'Kozue Route'}
HEROINES = {'梨深': 'Rimi', '七海': 'Nanami', '優愛': 'Yua', 'あやせ': 'Ayase', 'セナ': 'Sena', '梢': 'Kozue',
            'ディソード': 'DI-sword', 'ｂｌｕｅ ｓｋｙ': 'Blue Sky', 'スク水？メガネ？': 'Swimsuit? Glasses?'}
FW = str.maketrans('０１２３４５６７８９ＡＢＣＤＥＦ', '0123456789ABCDEF')

# speakers that never get a name field in CoZ's script; named in CoZ's style ("Girl A", "Pedestrian 1")
EXTRA_NAMES = {
    '藤田': 'Fujita', '女子高生': 'High School Girl', 'ゾンビ風集団': 'Zombie-like Crowd',
    '男子高校生': 'High School Boy', '若い女': 'Young Woman', '若い男': 'Young Man',
    '通行人女': 'Female Pedestrian', '通行人男': 'Male Pedestrian', '梨深＆梢': 'Rimi & Kozue',
}


def extra_name(jp):
    """display name -> English using EXTRA_NAMES, keeping a trailing Ａ/１ style suffix"""
    m = re.fullmatch(r'(.*?)([Ａ-Ｆ０-９]*)', jp)
    base, suf = m.group(1), m.group(2).translate(FW)
    if base in EXTRA_NAMES:
        return EXTRA_NAMES[base] + (' ' + suf if suf else '')
    return None


def chapter(jp):
    """第１０章 -> Chapter 10"""
    m = re.fullmatch(r'第([０-９]+)章', jp)
    return 'Chapter %s' % m.group(1).translate(FW) if m else None


def title(jp):
    return CHAPTER_TITLES.get(jp) or ROUTES.get(jp) or chapter(jp)


# Developer-only labels (シナリオ初期化, フローチャート, デバッグメニュー, 実験用, delusion-trigger and
# YES/NO jump labels) stay Japanese: the title menu's Latin-only font leaves them invisible, which
# is how the retail game hides them. Translating them would expose the debug menu.
GENERAL = {
    '%T1　【%T2】': '%T1 [%T2]',
}


def bracket_title(t):
    """【ｂｌｕｅ ｓｋｙ】 -> [Blue Sky]"""
    return re.sub(r'【([^】]*)】', lambda m: '[%s]' % (title(m.group(1)) or MENU_WORDS.get(m.group(1), m.group(1))), t)


MENU_WORDS = {'Ｃｌｅａｒ Ｌｉｓｔ': 'Clear List', 'ＣＧ Ｇａｌｌｅｒｙ': 'CG Gallery', 'Ｍｕｓｉｃ Ｇａｌｌｅｒｙ': 'Music Gallery',
              'メッセージ既読率': 'Message Read Rate', 'Ｓｈｏｒｔｃｕｔ': 'Shortcut'}


def shortcut(jp):
    """chapter-jump menu (SHORTCUT.BIN)"""
    m = re.fullmatch(r'(.+?)　(【[^】]*】)　から', jp)
    if m:
        return 'From %s %s' % (title(m.group(1)), bracket_title(m.group(2)))
    m = re.fullmatch(r'(.+?)の先頭から開始します。(?:%N(【[^】]*】)エンドを迎えます。)?', jp)
    if m:
        s = 'Start from the beginning of %s.' % title(m.group(1))
        if m.group(2):
            s += '%%NThis will lead to the %s ending.' % bracket_title(m.group(2))
        return s
    return None


def clearlist(jp):
    """clear list / unlock notices (CLRFLG.BIN)"""
    m = re.fullmatch(r'((?:%CF[0-9A-F]{4})?)(【[^】]*】)エンド((?:%CE)?)', jp)
    if m:
        return '%s%s Ending%s' % (m.group(1), bracket_title(m.group(2)), m.group(3))
    m = re.fullmatch(r'(Ｅｘｔｒａ|Ｃｏｎｔｉｎｕｅ)の%N(%CF[0-9A-F]{4})(【[^】]*】)%CE%Nが使用可能になりました。', jp)
    if m:
        where = {'Ｅｘｔｒａ': 'Extra', 'Ｃｏｎｔｉｎｕｅ': 'Continue'}[m.group(1)]
        return '%s%s%%CE%%Nis now available in %s.' % (m.group(2), bracket_title(m.group(3)), where)
    m = re.fullmatch(r'Ｃｌｅａｒ Ｌｉｓｔに%N(%CF[0-9A-F]{4})(【[^】]*】)%CE%Nが追加されました。', jp)
    if m:
        return '%s%s%%CE%%Nhas been added to the Clear List.' % (m.group(1), bracket_title(m.group(2)))
    return None


MENU_HELP = {
    '新しくゲームを始めます。': 'Start a new game.',
    'ゲームを前回プレイしたところから再開します。': 'Resume from where you last played.',
    '前回プレイした最後の状況から再開します。': 'Resume from your last game session.',
    'セーブしたところから再開します。': 'Resume from saved data.',
    'クイックセーブしたところから再開します。': 'Resume from quick save data.',
    'ゲーム環境の設定、確認を行います。': 'Check and change game settings.',
    'プレイマニュアルを表示します。': 'View the game manual.',
    'システムデータのロードを行います。': 'Load system data.',
    'システムデータのセーブを行います。': 'Save system data.',
    'イベント絵や、ＢＧＭ試聴などができます。': 'View event CGs, listen to music, and more.',
    'ゲームの達成度、プレイ時間等が確認できます。': 'Check your completion rate, play time, and more.',
    'ゲーム中のイベントＣＧを鑑賞できます。': 'View event CGs from the game.',
    'ゲーム中のＢＧＭを視聴できます。': 'Listen to music from the game.',
    'ゲーム中のムービーを鑑賞できます。': 'Watch movies from the game.',
    '声優さんからのお祝いのコメントが聞けます。': 'Listen to celebratory comments from the voice cast.',
    'キャラクターのプロフィールが確認できます。': 'View character profiles.',
    'ゲーム中の用語を調べられます。': 'Look up terms used in the game.',
    '進行状況を表すフローチャートが確認できます。': 'View the flowchart showing your progress.',
    '幻想界のフローチャートが確認できます。': 'View the flowchart for the Delusion World.',
    '現実界のフローチャートが確認できます。': 'View the flowchart for the Real World.',
}

# full names (CoZ order: family name first)
FULL_NAMES = {
    '西條 拓巳': 'Nishijou Takumi', '咲畑 梨深': 'Sakihata Rimi', '西條 七海': 'Nishijou Nanami',
    '楠 優愛': 'Kusunoki Yua', '岸本 あやせ': 'Kishimoto Ayase', '蒼井 セナ': 'Aoi Sena',
    '折原 梢': 'Orihara Kozue', '星来 オルジェル': 'Seira Orgel', '三住 大輔': 'Misumi Daisuke',
    '判 安二': 'Ban Yasuji', '諏訪 護': 'Suwa Mamoru', '百瀬 克子': 'Momose Katsuko',
    '高科 史男': 'Takashina Fumio', '葉月 志乃': 'Hazuki Shino', '野呂瀬 玄一': 'Norose Gen’ichi',
    '将軍': 'Shogun', '波多野 一成': 'Hatano Kazunari', 'その他': 'Other Characters',
}

SYSTEM_CFG = {
    'ブルー': 'Blue', 'ピンク': 'Pink', 'グリーン': 'Green', 'イエロー': 'Yellow',
    '０％': '0%', '２５％': '25%', '５０％': '50%', '７５％': '75%', '１００％': '100%',
    'サンプルメッセージ%Nカオス；ヘッド ノア%NあいうえおアイウエオＡＢＣＤＥ０１２３４５６７８９':
        'Sample Message%NCHAOS;HEAD NOAH%NABCDEabcde 0123456789',
}


def system_cfg(jp):
    if jp in SYSTEM_CFG:
        return SYSTEM_CFG[jp]
    m = re.fullmatch(r'(.+)の音声', jp)
    if m and m.group(1) in FULL_NAMES:
        return 'Voice: %s' % FULL_NAMES[m.group(1)]
    m = re.fullmatch(r'(.+)の音声の有無を設定します。', jp)
    if m and m.group(1) in FULL_NAMES:
        return 'Turns %s’s voice on or off.' % FULL_NAMES[m.group(1)] if m.group(1) != 'その他' \
            else 'Turns the voices of all other characters on or off.'
    return None


def clrlst(jp):
    m = re.fullmatch(r'(.*?)(【[^】]*】)', jp)
    if m:
        route = ROUTES.get(m.group(1))
        e = ((route + ' ') if route else '') + bracket_title(m.group(2))
        import enc
        if enc.width(e) > CLRLST_WIDTH:          # keep CoZ's words; 2 px spaces so it clears the scrollbar
            e = e.replace(' ', ' ')
        return e
    return None


CLRLST_WIDTH = 340   # px at message size; the list draws at ~0.89x and the scrollbar starts ~330 px in


def general(jp):
    if jp in GENERAL:
        return GENERAL[jp]
    t = title(jp)
    if t:
        return t
    return None
