import anthropic
import streamlit as st
from dotenv import load_dotenv

from cites_engine import CitesAssessment, assess_query, get_client

load_dotenv()

st.set_page_config(page_title="CITES Wildlife Trade Copilot", page_icon="🐢")

EXAMPLES = [
    "我想从泰国买一只巴西龟带到新加坡，可以吗？",
    "Can I bring a seahorse souvenir home from Thailand to the US?",
    "我在越南买了一个象牙雕刻品，能带回中国吗？",
]

APPENDIX_COLOR = {
    "I": "🔴",
    "II": "🟠",
    "III": "🟡",
    "Not listed": "🟢",
    "Uncertain": "⚪",
}

st.title("🐢 CITES Wildlife Trade Copilot")
st.caption("AI Product Demo · Claude API + Streamlit")

st.warning(
    "**这是一个产品原型 / demo，不是法律意见。** CITES物种清单、各国国内法规会变化，"
    "实际出行前请以 [CITES官方物种数据库 Species+](https://speciesplus.net) 和目的地国家"
    "CITES管理机构的信息为准。\n\n"
    "**This is a prototype demo, not legal advice.** Always verify against the official "
    "CITES Species+ database and your destination country's CITES Management Authority "
    "before traveling."
)

if "question" not in st.session_state:
    st.session_state.question = ""

st.write("**试试这些例子 / Try an example:**")
cols = st.columns(len(EXAMPLES))
for col, example in zip(cols, EXAMPLES):
    if col.button(example, use_container_width=True):
        st.session_state.question = example

question = st.text_area(
    "描述你的情况 / Describe your situation",
    key="question",
    placeholder="例：我想从泰国购买一只某某龟带到新加坡，可以吗？",
    height=90,
)

submitted = st.button("分析 / Analyze", type="primary")

if submitted:
    if not question.strip():
        st.error("请输入一个问题 / Please enter a question first.")
    else:
        try:
            client = get_client()
        except RuntimeError as e:
            st.error(str(e))
            st.stop()

        with st.spinner("正在查询CITES规则... / Checking CITES rules..."):
            try:
                result: CitesAssessment = assess_query(client, question)
            except anthropic.AuthenticationError:
                st.error("API key无效，请检查 .env 文件 / Invalid API key - check your .env file.")
                st.stop()
            except anthropic.RateLimitError:
                st.error("请求太频繁，请稍后再试 / Rate limited - please try again shortly.")
                st.stop()
            except anthropic.APIStatusError as e:
                st.error(f"API错误 / API error: {e.message}")
                st.stop()
            except Exception:
                st.error(
                    "AI返回的内容格式不符合预期，请换个问法或稍后重试 / "
                    "Claude's response didn't match the expected format - try rephrasing or retry."
                )
                st.stop()

        st.divider()
        st.subheader("📝 结论 / Bottom line")
        st.info(result.plain_summary)

        st.subheader("🔍 物种识别 / Species Identification")
        sp = result.species_identification
        c1, c2 = st.columns(2)
        c1.metric("最可能物种 / Likely species", sp.likely_common_name)
        c2.metric("置信度 / Confidence", sp.confidence)
        st.caption(f"*{sp.likely_scientific_name}* — {sp.note}")

        st.subheader("⚖️ CITES等级 / CITES Appendix")
        st.markdown(f"### {APPENDIX_COLOR.get(result.cites_appendix, '⚪')} Appendix {result.cites_appendix}")
        st.write(result.appendix_explanation)

        st.subheader("🚫 贸易限制 / Trade Restrictions")
        st.write(result.trade_restrictions)

        st.subheader("📄 所需Permit / Required Permits")
        for permit in result.required_permits:
            st.markdown(f"- {permit}")

        st.subheader("⚠️ 风险提示 / Risk Warnings")
        for risk in result.risk_warnings:
            st.markdown(f"- {risk}")

        st.subheader("📚 信息来源 / Sources")
        for source in result.sources:
            st.markdown(f"- {source}")
