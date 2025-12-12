    with st.status("🔍 Fetching live Kenyan market data...", expanded=True) as status:
        results = searx_fetch(phone)
        searx_ok = len(results) > 0

        if searx_ok:
            with st.expander("👀 Preview raw Kenyan results (before AI)"):
                df_raw = pd.DataFrame(results)
                st.dataframe(df_raw, use_container_width=True)
                st.metric("Kenyan results", len(results))

            ctx = build_context(results)
            price_block, specs_block, insights_block, copy_block = prompt_with_data(phone, ctx, persona, tone)
        else:
            # Brand-only fallback
            price_block = specs_block = insights_block = ""
            price_block, specs_block, insights_block, copy_block = prompt_without_data(phone, persona, tone)

        status.update(label="✅ Kit ready!", state="complete", expanded=False)
