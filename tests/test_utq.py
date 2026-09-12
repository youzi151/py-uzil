from __future__ import annotations

from uzilpy.utq import UTQ, Tag


def keys(result: dict) -> list[str]:
    return list(result.keys())


def test_inst_reuses_key():
    utq = UTQ()
    a = utq.inst("test_simple")
    b = utq.inst("test_simple")
    other = utq.inst("other")
    once = utq.once()
    default = utq.inst()
    assert a is b
    assert other is not a
    assert once is not a
    assert default is utq.inst("_")
    assert once is not default


def test_simple_search():
    utq = UTQ()
    inst = utq.inst("test_simple")
    inst.set_data("Aman", ["role:dps", "gender:male"])
    inst.set_data("Bwoman", ["role:tank", "gender:female"])
    c_sup = Tag(scope="role", val="sup")
    c_male = Tag(scope="gender", val="male")
    inst.set_data("Cman", [c_sup, c_male])
    inst.set_data("Dman", ["role:sup,tank", "gender:male"])

    assert keys(inst.search("-role:dps gender:male")) == ["Cman", "Dman"]
    assert keys(inst.search("role:sup - role : tank")) == ["Cman"]


def test_set_data_splits_same_scope():
    inst = UTQ().once()
    inst.set_data("Dman", ["role:sup,tank", "gender:male"])
    stored = inst.get_data("Dman")
    assert stored is not None
    assert [(t.scope, t.val) for t in stored] == [
        ("role", "sup"),
        ("role", "tank"),
        ("gender", "male"),
    ]


def test_stored_string_roundtrip():
    tag = Tag(scope="series", val="S1", attr="@")
    assert tag.to_stored_string() == "@series:S1"
    inst = UTQ().once()
    inst.set_data("book", "series:S1, S2 role:tank")
    assert [t.to_stored_string() for t in inst.get_data("book")] == [
        "series:S1",
        "series:S2",
        "role:tank",
    ]


def _weapons():
    inst = UTQ().once()
    inst.set_data(
        "鐵劍(火球術)",
        [
            "類型:物理",
            "類型:劍",
            "材質:金屬",
            "稀有度:常見",
            "需求:力量",
            "重量:中",
            "範圍:近",
            "附魔:火球術",
        ],
    )
    inst.set_data(
        "鐵斧",
        [
            "類型:物理",
            "類型:斧",
            "材質:金屬",
            "稀有度:常見",
            "需求:力量",
            "重量:中",
            "範圍:近",
        ],
    )
    inst.set_data(
        "雷錘",
        [
            "類型:武器",
            "類型:錘",
            "材質:金屬",
            "稀有度:稀有",
            "需求:敏捷",
            "重量:重",
            "範圍:近",
            "範圍:遠",
            "屬性:聖",
            "屬性:雷",
        ],
    )
    inst.set_data(
        "冰霜大劍",
        [
            "類型:物理",
            "類型:劍",
            "類型:大劍",
            "材質:金屬",
            "稀有度:稀有",
            "需求:力量",
            "重量:重",
            "範圍:近",
            "屬性:冰",
        ],
    )
    inst.set_data(
        "火掌",
        [
            "類型:魔法",
            "類型:拳掌",
            "材質:皮革",
            "稀有度:稀有",
            "需求:智力",
            "重量:輕",
            "範圍:近",
            "屬性:火",
        ],
    )
    inst.set_data(
        "火焰杖",
        [
            "類型:魔法",
            "類型:杖",
            "材質:木頭",
            "材質:紅寶石",
            "稀有度:稀有",
            "需求:智力",
            "重量:輕",
            "範圍:遠",
            "屬性:火",
        ],
    )
    inst.set_data(
        "冰霜杖",
        [
            "類型:魔法",
            "類型:杖",
            "材質:木頭",
            "材質:藍寶石",
            "稀有度:稀有",
            "需求:智力",
            "重量:中",
            "範圍:遠",
            "屬性:冰",
        ],
    )
    inst.set_data(
        "長弓",
        [
            "類型:物理",
            "類型:弓",
            "材質:木頭",
            "稀有度:常見",
            "需求:敏捷",
            "重量:中",
            "範圍:遠",
        ],
    )
    inst.set_data(
        "聖火弩",
        [
            "類型:物理",
            "類型:弩",
            "材質:木頭",
            "材質:金屬",
            "稀有度:稀有",
            "需求:敏捷",
            "重量:重",
            "範圍:遠",
            "屬性:聖",
            "屬性:火",
        ],
    )
    return inst


def test_scenario_basic_queries():
    inst = _weapons()
    assert keys(inst.search("+類型:劍")) == ["鐵劍(火球術)", "冰霜大劍"]
    assert keys(inst.search("+[類型:劍, 斧]")) == ["鐵劍(火球術)", "鐵斧", "冰霜大劍"]
    assert keys(inst.search("類型:魔法 +[屬性:火, 冰]")) == ["火掌", "火焰杖", "冰霜杖"]
    assert keys(inst.search("屬性:. -屬性:.^火")) == ["火掌", "火焰杖"]
    assert keys(inst.search("稀有度:稀有 -類型:物理 *附魔:. --屬性:聖")) == [
        "鐵劍(火球術)",
        "火掌",
        "火焰杖",
        "冰霜杖",
    ]


def test_scenario_advanced_queries():
    inst = _weapons()
    assert keys(inst.search("稀有度:神話 > 稀有度:稀有 > 稀有度:常見")) == [
        "雷錘",
        "冰霜大劍",
        "火掌",
        "火焰杖",
        "冰霜杖",
        "聖火弩",
    ]
    all_names = [
        "鐵劍(火球術)",
        "鐵斧",
        "雷錘",
        "冰霜大劍",
        "火掌",
        "火焰杖",
        "冰霜杖",
        "長弓",
        "聖火弩",
    ]
    ice_ranged_or_fire_melee = {"冰霜杖", "火掌"}
    assert keys(inst.search(". % (屬性:冰 範圍:遠 | 屬性:火 範圍:近)")) == [
        name for name in all_names if name not in ice_ranged_or_fire_melee
    ]

    assert keys(inst.search(". % (屬性:. 範圍:近 | (屬性:聖 & *範圍:遠 *類型:魔法)")) == [
        "鐵劍(火球術)",
        "鐵斧",
        "火焰杖",
        "冰霜杖",
        "長弓",
    ]
