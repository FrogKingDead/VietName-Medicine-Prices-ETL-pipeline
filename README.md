# VietName-Medicine-Prices-ETL-pipeline
This project is about automating the data pipeline for public pharmaceutical registries.  

For the project, we have used technology like Docker, Python, and MongoDB Atlas to create an ETL pipeline with a workflow that first extracts over 26,000 raw documents from a public API and stages them completely intact in a landing zone database. A downstream transformation script then runs these records through a strict dual-layer quality gate, using regular expressions (Regex) to tackle the incredibly messy active ingredient fields.  
  
What we achieve is a cleaned, structured database that parses chaotic ingredient strings, isolates substance names, flattens compound liquid ratios (like 125mg/5ml), and maps individual components to distinct data fields with around 95% data retention rate. 
   
We also have graphs built with Streamlit, Pandas, and Seaborn to visualize the final result—showing interactive distributions of top exporting nations, stepped medicine pricing tiers, top manufacturer volumes, premium drug profiles, and historical registration timelines over a unified web dashboard.