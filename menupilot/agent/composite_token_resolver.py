"""
Composite Token Resolver — 跨类别粘连 token 拆分。

仅用于 chowbus 管线：chowbus 模板的 customization option 列可能将两个
不同类别的属性值塞入同一个单元格（如 "中杯牛奶" = 规格+奶底），
导致后续 token_classifier 无法识别。本模块在 collect_chowbus_rows 之后、
classify_single 之前介入，检测并拆分跨类别粘连。

算法：
  1. 快速路径：整词在 TOKEN_MAP 中 → 直接返回
  2. 尝试所有二分点：若左侧和右侧均为已知 token 且类别不同 → 拆分
  3. 递归处理拆分后的两部分
  4. 无有效拆分点 → 保守保留原词
"""

from typing import List

from menupilot.data.token_dict import TOKEN_MAP


def resolve_composite(token: str) -> List[str]:
    """检测并拆分跨类别粘连的复合 token。

    仅在两端均可独立识别为不同类别的已知 token 时才拆分。
    无法拆分时返回原词的单元素列表。

    Args:
        token: 单个单元格清洗后的中文值，如 "中杯牛奶"、"正常冰"。

    Returns:
        拆分后的 token 列表。已知整词和无法拆分的返回单元素列表。

    Examples:
        >>> resolve_composite("中杯牛奶")
        ['中杯', '牛奶']
        >>> resolve_composite("正常冰")
        ['正常冰']
        >>> resolve_composite("锡兰红茶")
        ['锡兰红茶']
    """
    if not token:
        return []

    result = _expand_one(token)
    return result if result else []


def resolve_all(tokens: List[str]) -> List[str]:
    """对 token 列表逐条执行跨类别拆分。

    Args:
        tokens: 清洗后的 token 列表（来自 collect_chowbus_rows 的 chinese_values）。

    Returns:
        展开后的 token 列表，粘连项被替换为其子 token。
    """
    if not tokens:
        return []

    result = []
    for token in tokens:
        expanded = resolve_composite(token)
        result.extend(expanded)
    return result


def _expand_one(text: str) -> List[str]:
    """递归拆分单个 token。

    策略：
      1. 整词命中 TOKEN_MAP → 直接返回（快速路径）
      2. 遍历二分点，找「左侧已知 + 右侧已知 + 类别不同」的最优拆分
      3. 找到后递归处理左右两侧
      4. 找不到 → 保守保留原词
    """
    # 快速路径：整词已知
    if text in TOKEN_MAP:
        return [text]

    # 找最优二分点：两端都是已知 token 且类型不同
    best_pos = -1
    for i in range(1, len(text)):
        left, right = text[:i], text[i:]
        left_type = TOKEN_MAP.get(left)
        right_type = TOKEN_MAP.get(right)
        if left_type and right_type and left_type != right_type:
            # 取最长左侧匹配（更保守的拆分点）
            if i > best_pos:
                best_pos = i

    if best_pos > 0:
        left_parts = _expand_one(text[:best_pos])
        right_parts = _expand_one(text[best_pos:])
        return left_parts + right_parts

    # 无法拆分 → 保留原词
    return [text]


# ═══════════════════════════════════════════════════════════════════
# 自测
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    passed = 0
    failed = 0

    def check(condition, msg):
        global passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {msg}")
        else:
            failed += 1
            print(f"  FAIL  {msg}")

    print("=== Composite Token Resolver 自测 ===\n")

    # ── 1. 跨类别粘连 → 拆分 ──
    print("1. 跨类别粘连 — 应拆分")
    check(resolve_composite("中杯牛奶") == ["中杯", "牛奶"],
          "中杯牛奶 → [中杯, 牛奶]")
    check(resolve_composite("大杯燕麦奶") == ["大杯", "燕麦奶"],
          "大杯燕麦奶 → [大杯, 燕麦奶]")
    check(resolve_composite("中杯椰乳") == ["中杯", "椰乳"],
          "中杯椰乳 → [中杯, 椰乳]")
    check(resolve_composite("少冰七分糖") == ["少冰", "七分糖"],
          "少冰七分糖 → [少冰, 七分糖]")
    check(resolve_composite("去冰无糖") == ["去冰", "无糖"],
          "去冰无糖 → [去冰, 无糖]")
    check(resolve_composite("温热全糖") == ["温热", "全糖"],
          "温热全糖 → [温热, 全糖]")
    print()

    # ── 2. 已知整词 → 保持不变 ──
    print("2. 已知整词 — 不变")
    check(resolve_composite("正常冰") == ["正常冰"],
          "正常冰 → [正常冰]")
    check(resolve_composite("七分糖") == ["七分糖"],
          "七分糖 → [七分糖]")
    check(resolve_composite("热") == ["热"],
          "热 → [热]")
    check(resolve_composite("五角瓶") == ["五角瓶"],
          "五角瓶 → [五角瓶]")
    check(resolve_composite("红茶") == ["红茶"],
          "红茶 → [红茶]")
    check(resolve_composite("五角排红茶") == ["五角排红茶"],
          "五角排红茶 → [五角排红茶]")
    check(resolve_composite("五黄标准茶") == ["五黄标准茶"],
          "五黄标准茶 → [五黄标准茶]")
    print()

    # ── 3. 至少一端未知 → 保守保留 ──
    print("3. 至少一端未知 — 保守保留")
    check(resolve_composite("默认中杯") == ["默认中杯"],
          "默认中杯 → 不变（'默认'未知）")
    check(resolve_composite("锡兰红茶") == ["锡兰红茶"],
          "锡兰红茶 → 不变（'锡兰'未知）")
    check(resolve_composite("杯装密封") == ["杯装密封"],
          "杯装密封 → 不变（全部未知）")
    check(resolve_composite("不加糖") == ["不加糖"],
          "不加糖 → 不变（'不加'未知）")
    print()

    # ── 4. 边界 ──
    print("4. 边界场景")
    check(resolve_composite("") == [],
          "空字符串 → []")
    check(resolve_composite("中") == ["中"],
          "单字未知 → 保留")
    print()

    # ── 5. resolve_all 批量 ──
    print("5. resolve_all 批量")
    batch = ["中杯牛奶", "红茶", "正常冰", "少冰七分糖", "锡兰红茶"]
    result = resolve_all(batch)
    check(result == ["中杯", "牛奶", "红茶", "正常冰", "少冰", "七分糖", "锡兰红茶"],
          f"批量拆分正确 → {result}")
    print()

    # ── 6. 模拟实际 chowbus composite_info 效果 ──
    print("6. 模拟 chowbus composite_info 重建")
    # 原始 cell 值（粘连前）
    raw_cells = ["中杯牛奶", "红茶", "正常冰", "七分糖"]
    # 经过 resolver
    resolved = resolve_all(raw_cells)
    composite_info = ", ".join(resolved)
    check(composite_info == "中杯, 牛奶, 红茶, 正常冰, 七分糖",
          f"重建后 composite_info → {composite_info}")
    print()

    # ── 汇总 ──
    print(f"=== 结果: {passed} passed, {failed} failed ===")
