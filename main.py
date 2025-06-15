from sentence_transformers import SentenceTransformer, util
from pandas import DataFrame, read_excel
from loguru import logger
from click import command, option, Path
from tqdm import tqdm


@logger.catch
def process_document(
    file: str,
    model_name: str, 
    threshold: float,
    show_progress: bool
):
    logger.info("Запускаем модель")
    model = SentenceTransformer(model_name)
    logger.info(f"Start process, threshold {threshold}")
    df = read_excel(file, engine='openpyxl')
    df.set_index(df.iloc[:, 0], inplace=True)
    result_df: DataFrame = DataFrame()
    logger.info("Токенезируем предложения")
    embeddings = model.encode(
        list(i.iloc[1] for _, i in df.iterrows())
    )
    logger.info("Ищем кластеры")
    clusters = util.community_detection(
        embeddings,
        threshold=threshold,
        min_community_size=3,
        show_progress_bar=show_progress
    )
    
    def generate_records():
        for cluster in tqdm(clusters, total=len(clusters), desc='Формируем таблицу, изучаем кластеры'):
            yield from (
                {'id': df.iloc[i, 0], 'text': df.iloc[i, 1]} for i in cluster
            )
            yield {'id': None, 'text': None}

    result_df = DataFrame.from_records(
        generate_records()
    )

    return result_df

@command()
@option('-i', '--input', type=Path(exists=True, readable=True))
@option('-o', '--output', type=Path(writable=True))
@option('-m', '--model', type=str, default='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
@option('-t', '--threshold', type=float, help="Параметр близости", default=.9)
@option('-p', '--progress', is_flag=True, default=True, help='Показывать прогресс')
def main(input, output, model, threshold, progress):
    df = process_document(
        input, model, threshold, progress
    )
    df.to_excel(output)


if __name__ == "__main__":
    main()
