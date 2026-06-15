import streamlit as st
import pymongo
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "vietnam_pharma_raw")
CLEAN_COLLECTION = os.environ.get("CLEAN_COLLECTION_NAME", "clean_drug_registry")

@st.cache_data
def load_clean_data():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[CLEAN_COLLECTION]
    
    cursor = collection.find({}, {
        "name": 1, 
        "manufacturer": 1, 
        "registrant": 1,
        "countryOfOrigin": 1, 
        "dosageForm": 1, 
        "pricePerUnit": 1, 
        "ingredients": 1, 
        "publicationDate": 1,
        "status": 1,
        "_id": 0
    })
    return pd.DataFrame(list(cursor))

st.set_page_config(page_title="Vietnam Pharma Analytics", layout="wide")
st.title("Vietnam Pharmaceutical Data Registry Analytics")
st.markdown("---")

try:
    df = load_clean_data()
    
    if df.empty:
        st.warning("Database connected, but clean collection appears to be empty.")
    else:
        # --- METRIC CARDS ---
        total_drugs = len(df)
        valid_prices = df[df["pricePerUnit"] > 0]
        avg_price = valid_prices["pricePerUnit"].median() if not valid_prices.empty else 0
        unique_manufacturers = df["manufacturer"].nunique() if "manufacturer" in df.columns else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Sanitized Records", f"{total_drugs:,}")
        col2.metric("Median Wholesale Price (VND)", f"{int(avg_price):,}đ")
        col3.metric("Registered Manufacturers", f"{unique_manufacturers:,}")
        
        st.markdown("### Market and Supply Chain Distribution")
        layout_col1, layout_col2 = st.columns(2)

        # CHART 1: Top 10 Manufacturing Nations
        with layout_col1:
            st.subheader("Top 10 Medicine Supplying Nations")
            if "countryOfOrigin" in df.columns:
                df["countryOfOrigin"] = df["countryOfOrigin"].fillna("Unknown").str.strip()
                nation_counts = df["countryOfOrigin"].value_counts().head(10)
                fig, ax = plt.subplots(figsize=(6, 4))
                sns.barplot(x=nation_counts.values, y=nation_counts.index, ax=ax, palette="viridis")
                ax.set_xlabel("Number of Registered Medications")
                st.pyplot(fig)
            else:
                st.info("Key 'countryOfOrigin' missing from data collection.")

        # CHART 2: Pricing Ranges
        with layout_col2:
            st.subheader("Medication Count by Ordered Price Ranges")
            if "pricePerUnit" in df.columns:
                # Define deterministic categorical bins for custom market grouping
                bins = [-1, 10000, 20000, 50000, 200000, 500000, 2000000, float('inf')]
                labels = ["< 10k VND", "10k - 20k VND", "20k - 50k VND", "50k - 200k VND", "200k - 500k VND", "500k - 2M VND", "> 2M VND"]
                
                price_analytics = df.copy()
                price_analytics["PriceRange"] = pd.cut(price_analytics["pricePerUnit"], bins=bins, labels=labels)
                range_counts = price_analytics["PriceRange"].value_counts().reindex(labels)
                
                fig, ax = plt.subplots(figsize=(6, 4))
                sns.barplot(x=range_counts.index, y=range_counts.values, ax=ax, palette="rocket")
                ax.set_ylabel("Number of Medications")
                plt.xticks(rotation=15)
                st.pyplot(fig)
            else:
                st.info("Key 'pricePerUnit' missing from data collection.")

        st.markdown("---")
        st.markdown("### Operational and Stakeholder Tracking")
        layout_col3, layout_col4 = st.columns(2)

        # CHART 3: Top 5 manufacturers
        with layout_col3:
            st.subheader("Top 5 Manufacturing Entities")
            if "manufacturer" in df.columns:
                df["manufacturer"] = df["manufacturer"].fillna("Unknown").str.strip()
                top_manufacturers = df["manufacturer"].value_counts().head(5)
                fig, ax = plt.subplots(figsize=(6, 3.5))
                # Truncate long company names for neat visual layout
                short_labels = [label[:35] + "..." if len(label) > 35 else label for label in top_manufacturers.index]
                sns.barplot(x=top_manufacturers.values, y=short_labels, ax=ax, palette="crest")
                ax.set_xlabel("Volume Registered")
                st.pyplot(fig)

        # CHART 4: Top 5 Registrators
        with layout_col4:
            st.subheader("Top 5 Submitting Registrators")
            if "registrant" in df.columns:
                df["registrant"] = df["registrant"].fillna("Unknown").str.strip()
                top_Registrators = df["registrant"].value_counts().head(5)
                fig, ax = plt.subplots(figsize=(6, 3.5))
                short_decl = [label[:35] + "..." if len(label) > 35 else label for label in top_Registrators.index]
                sns.barplot(x=top_Registrators.values, y=short_decl, ax=ax, palette="mako")
                ax.set_xlabel("Volume Declared")
                st.pyplot(fig)

        st.markdown("---")
        st.markdown("### Structural and Lifecycle Analytics")
        layout_col5, layout_col6 = st.columns(2)

        # CHART 5: Medicine Formulations Profile
        with layout_col5:
            st.subheader("Medicine Formulations Profile")
            if "dosageForm" in df.columns:
                df["dosageForm"] = df["dosageForm"].fillna("Unclassified").str.strip()
                type_counts = df["dosageForm"].value_counts().head(10)
                fig, ax = plt.subplots(figsize=(6, 4))
                sns.barplot(x=type_counts.values, y=type_counts.index, ax=ax, palette="plasma")
                st.pyplot(fig)
                
        # CHART 6: Registry Status 
        with layout_col6:
            st.subheader("Registry Status Tracking")
            if "status" in df.columns:
                df["status"] = df["status"].fillna("No Data").str.strip()
                status_counts = df["status"].value_counts()
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%', startangle=140, colors=sns.color_palette("Pastel1"))
                st.pyplot(fig)

        # CHART 7: Medicine Registration Timeline
        st.markdown("---")
        st.subheader("Medicine Registration Timeline Distribution")
        if "publicationDate" in df.columns:
            df["pub_date"] = pd.to_datetime(df["publicationDate"], errors="coerce")
            timeline_df = df.dropna(subset=["pub_date"]).copy()

            if not timeline_df.empty:
                timeline_df["Year-Month"] = timeline_df["pub_date"].dt.to_period("M")
                time_series = timeline_df.groupby("Year-Month").size().to_frame("Count").reset_index()
                time_series["Year-Month"] = time_series["Year-Month"].astype(str)
                fig, ax = plt.subplots(figsize=(12, 4))
                sns.lineplot(data=time_series, x="Year-Month", y="Count", marker="o", color="#1f77b4", linewidth=2.5)
                plt.xticks(rotation=45)
                st.pyplot(fig)
                
        # CHART 8: Frequently Used Ingredients
        st.markdown("---")
        st.subheader("Most Frequently Used Active Ingredients")
        if "ingredients" in df.columns:
            all_ingredients = []
            for ing_list in df["ingredients"].dropna():
                for ing in ing_list:
                    if isinstance(ing, dict) and ing.get("name"):
                        all_ingredients.append(ing.get("name"))
                        
            if all_ingredients:
                ing_df = pd.Series(all_ingredients).value_counts().head(15)
                fig, ax = plt.subplots(figsize=(12, 5))
                sns.barplot(x=ing_df.values, y=ing_df.index, palette="mako", ax=ax)
                ax.set_xlabel("Occurrences across Registry")
                st.pyplot(fig)

except Exception as e:
    st.error(f"Could not load data from MongoDB cluster: {e}")