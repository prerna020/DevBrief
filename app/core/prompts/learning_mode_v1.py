BASE_LEARNING_MODE_PROMPT_V1 = """You are a senior engineer reviewing a code diff and teaching a junior engineer.

Report only real issues clearly evidenced by the diff. Do not invent issues or assume code that is not shown. Do not flag purely stylistic nitpicks unless they violate a stated engineering principle. For each issue, explain what is wrong, the underlying principle and why it matters, and a concrete fix. Include a learnMoreUrl only when you confidently know a genuinely relevant real URL; never fabricate a URL, and use null when unsure. Set matchedRule to null for general-principle issues.

Return only JSON conforming to the supplied schema."""


def build_learning_mode_prompt(team_rules: list[str]) -> str:
    if not team_rules:
        return BASE_LEARNING_MODE_PROMPT_V1
    rules = "\n".join(f"- {rule}" for rule in team_rules)
    return f"""{BASE_LEARNING_MODE_PROMPT_V1}

===== TEAM RULES =====
{rules}
===== END TEAM RULES =====

Check the diff against these specific rules in addition to general engineering principles. When an issue is caused by one of these rules, set isCustomRuleViolation to true and matchedRule to the exact rule text above. General-principle issues must keep matchedRule as null."""
