import marimo

__generated_with = "0.23.1"
app = marimo.App(width="columns")


@app.cell
def _():
    import marimo as mo

    return


@app.cell
def _():
    return


@app.cell
def _():
    from google.cloud import bigquery

    client = bigquery.Client()

    query = """
        SELECT corpus AS title, COUNT(word) AS unique_words
        FROM `bigquery-public-data.samples.shakespeare`
        GROUP BY title
        ORDER BY unique_words
        DESC LIMIT 10
    """
    results = client.query(query)

    for row in results:
        title = row['title']
        unique_words = row['unique_words']
        print(f'{title:<20} | {unique_words}')
    return


if __name__ == "__main__":
    app.run()
