import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger
from main import process_document


# Router for handling all bot messages
form_router = Router()


class ProcessingState(StatesGroup):
    waiting_for_file = State()
    waiting_for_threshold = State()


# Global variable to store model name
MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'


@form_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command"""
    await message.answer(
        "👋 Привет! Я бот для поиска похожих текстов.\n\n"
        "Используйте /process чтобы начать обработку документа.\n"
        "Используйте /help для получения справки."
    )


@form_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command"""
    await message.answer(
        "📖 Справка:\n\n"
        "/start - Начать работу с ботом\n"
        "/process - Начать обработку документа\n"
        "/help - Показать эту справку\n\n"
        "Как использовать:\n"
        "1. Отправьте команду /process\n"
        "2. Загрузите Excel файл (.xlsx)\n"
        "3. Укажите порог схожести (по умолчанию 0.9)\n"
        "4. Получите обработанный файл с кластерами похожих текстов\n\n"
        f"Используемая модель: {MODEL_NAME}"
    )


@form_router.message(Command("process"))
async def cmd_process(message: Message, state: FSMContext) -> None:
    """Handle /process command"""
    await state.set_state(ProcessingState.waiting_for_file)
    await message.answer(
        "📄 Отправьте Excel файл (.xlsx) для обработки.\n"
        "Файл должен содержать ID в первом столбце и текст во втором столбце."
    )


@form_router.message(Command("cancel"))
@form_router.message(F.text.casefold() == "cancel")
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """Allow user to cancel any action"""
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("Cancelling state %r", current_state)
    await state.clear()
    await message.answer("Отменено.")


@form_router.message(ProcessingState.waiting_for_file, F.document)
async def handle_document(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle document upload"""
    document = message.document
    
    # Check file extension
    if not document.file_name.endswith('.xlsx'):
        await message.answer(
            "❌ Пожалуйста, отправьте файл в формате .xlsx (Excel)"
        )
        return
    
    # Download file
    file_path = f"temp_{message.from_user.id}_{document.file_name}"
    await bot.download(document, destination=file_path)
    
    # Store file path in state
    await state.update_data(file_path=file_path)
    await state.set_state(ProcessingState.waiting_for_threshold)
    
    await message.answer(
        "✅ Файл получен!\n\n"
        "Теперь укажите порог схожести (threshold) от 0 до 1.\n"
        "Рекомендуемое значение: 0.9\n\n"
        "Чем выше значение, тем более похожими должны быть тексты для попадания в один кластер.\n\n"
        "Отправьте число или отправьте 'default' для использования значения по умолчанию (0.9)"
    )


@form_router.message(ProcessingState.waiting_for_file)
async def handle_non_document(message: Message) -> None:
    """Handle non-document messages when waiting for file"""
    await message.answer(
        "⚠️ Пожалуйста, отправьте файл Excel (.xlsx) или используйте /cancel для отмены."
    )


@form_router.message(ProcessingState.waiting_for_threshold)
async def handle_threshold(message: Message, state: FSMContext) -> None:
    """Handle threshold input and process document"""
    # Parse threshold
    threshold = 0.9
    if message.text.lower() != 'default':
        try:
            threshold = float(message.text)
            if not 0 <= threshold <= 1:
                await message.answer(
                    "❌ Порог должен быть числом от 0 до 1. Попробуйте снова."
                )
                return
        except ValueError:
            await message.answer(
                "❌ Некорректное значение. Отправьте число от 0 до 1 или 'default'."
            )
            return
    
    # Get file path from state
    data = await state.get_data()
    file_path = data.get('file_path')
    
    if not file_path or not os.path.exists(file_path):
        await message.answer(
            "❌ Файл не найден. Пожалуйста, начните заново с команды /process"
        )
        await state.clear()
        return
    
    # Process document
    processing_msg = await message.answer(
        f"⏳ Обрабатываю документ с порогом {threshold}...\n"
        "Это может занять некоторое время."
    )
    
    try:
        logger.info(f"Processing document for user {message.from_user.id}")
        result_df = process_document(
            file=file_path,
            model_name=MODEL_NAME,
            threshold=threshold,
            show_progress=False
        )
        
        # Save result
        output_path = f"result_{message.from_user.id}_{os.path.basename(file_path)}"
        result_df.to_excel(output_path, index=False)
        
        # Send result file
        await message.answer_document(
            FSInputFile(output_path),
            caption=f"✅ Обработка завершена!\n\n"
                    f"Порог схожести: {threshold}\n"
                    f"Найдено кластеров: {len(result_df[result_df['id'].isna()])}"
        )
        
        # Cleanup
        os.remove(file_path)
        os.remove(output_path)
        
        logger.info(f"Successfully processed document for user {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        await message.answer(
            f"❌ Произошла ошибка при обработке файла:\n{str(e)}\n\n"
            "Проверьте, что файл имеет правильную структуру:\n"
            "- Первый столбец: ID\n"
            "- Второй столбец: текст для анализа"
        )
        
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
    
    finally:
        await processing_msg.delete()
        await state.clear()


async def main() -> None:
    """Main function to start the bot"""
    # Get token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return
    
    # Get optional model name from environment
    global MODEL_NAME
    MODEL_NAME = os.getenv(
        'MODEL_NAME',
        'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    )
    
    # Initialize Bot instance with default bot properties
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Initialize Dispatcher with memory storage
    dp = Dispatcher(storage=MemoryStorage())
    
    # Include the router
    dp.include_router(form_router)
    
    # Start event dispatching
    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

