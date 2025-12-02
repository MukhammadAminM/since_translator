"""Тест применения глоссария при переводе"""
import asyncio
import os
from services.translator import TranslationService

# Пробуем загрузить переменные окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Если dotenv не установлен, полагаемся на переменные окружения

async def test_translation_with_glossary():
    """Тестирует перевод с использованием глоссария"""
    
    print("=" * 60)
    print("Тест применения глоссария при переводе")
    print("=" * 60)
    
    # Инициализируем сервис перевода
    try:
        translator = TranslationService()
        print("✅ TranslationService инициализирован")
        
        if translator.glossary_manager:
            print(f"✅ GlossaryManager загружен")
            print(f"   Глоссариев: {len(translator.glossary_manager.glossaries)}")
            for lang, glossary in translator.glossary_manager.glossaries.items():
                print(f"   - {lang}: {len(glossary)} терминов")
        else:
            print("⚠️  GlossaryManager не загружен")
            return
        
    except Exception as e:
        print(f"❌ Ошибка инициализации: {str(e)}")
        return
    
    # Тестовый текст с терминами из глоссария
    test_texts = {
        "ru": "Ракета УРМ-1 запущена с космодрома. Используется баллистическая ракета и жидкостный ракетный двигатель.",
        "ar": "صاروخ - Missile / Rocket",
        "zh": "火箭 - Rocket"
    }
    
    print("\n" + "=" * 60)
    print("Тест 1: Проверка поиска релевантных терминов")
    print("=" * 60)
    
    # Проверяем поиск релевантных терминов
    test_text_ru = test_texts["ru"]
    relevant_terms = translator.glossary_manager._find_relevant_terms(
        test_text_ru, 
        "ru", 
        max_terms=10
    )
    
    print(f"\nТекст: '{test_text_ru}'")
    print(f"\nНайдено релевантных терминов: {len(relevant_terms)}")
    for term in relevant_terms[:5]:
        source = term.get('source', '')
        target = term.get('target', '')
        print(f"  - {source} -> {target}")
    
    print("\n" + "=" * 60)
    print("Тест 2: Проверка форматирования глоссария для промпта")
    print("=" * 60)
    
    # Проверяем форматирование глоссария
    glossary_summary = translator.glossary_manager.get_glossary_summary(
        source_lang="ru",
        text=test_text_ru,
        max_terms=10
    )
    
    print("\nГлоссарий для промпта (первые 500 символов):")
    print("-" * 60)
    print(glossary_summary[:500])
    print("-" * 60)
    
    print("\n" + "=" * 60)
    print("Тест 3: Проверка полного промпта (системное сообщение)")
    print("=" * 60)
    
    # Создаем промпт как в реальном переводе
    lang_names = {"ru": "Russian", "ar": "Arabic", "zh": "Chinese"}
    model_instructions = {
        "engineering": "Translate technical and engineering terminology precisely. Maintain technical accuracy and use appropriate engineering terminology."
    }
    
    glossary_text = ""
    if translator.glossary_manager:
        glossary_summary = translator.glossary_manager.get_glossary_summary(
            "ru", 
            text=test_text_ru,
            max_terms=200
        )
        if glossary_summary:
            glossary_text = f"\n\n{glossary_summary}"
    
    system_prompt = (
        f"You are a professional translator specializing in engineering translation. "
        f"Translate the following text from Russian to EN. "
        f"{model_instructions['engineering']} "
        f"Maintain the original formatting, paragraph structure, and line breaks. "
        f"Do not add any explanations, comments, or notes - provide only the translation."
        f"{glossary_text}"
    )
    
    print("\nСистемный промпт (первые 800 символов):")
    print("-" * 60)
    print(system_prompt[:800])
    if len(system_prompt) > 800:
        print(f"... (еще {len(system_prompt) - 800} символов)")
    print("-" * 60)
    
    # Проверяем, что глоссарий включен
    if "IMPORTANT" in system_prompt or "GLOSSARY" in system_prompt or "Use these exact translations" in system_prompt:
        print("\n✅ Глоссарий включен в промпт!")
    else:
        print("\n⚠️  Глоссарий не найден в промпте")
    
    print("\n" + "=" * 60)
    print("Тест 4: Реальный перевод (требует OpenAI API)")
    print("=" * 60)
    
    # Проверяем наличие API ключа
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY не найден. Пропускаем тест реального перевода.")
        print("   Для полного теста установите OPENAI_API_KEY в .env файле")
        return
    
    if not translator.client:
        print("⚠️  OpenAI клиент не инициализирован. Пропускаем тест реального перевода.")
        return
    
    print("\nВыполняем тестовый перевод...")
    try:
        translated = await translator.translate(
            text=test_text_ru,
            source_lang="ru",
            target_lang="en",
            model="engineering"
        )
        
        print(f"\nИсходный текст:")
        print(f"  {test_text_ru}")
        print(f"\nПереведенный текст:")
        print(f"  {translated}")
        
        # Проверяем, что термины из глоссария использованы
        glossary_terms = ["URM-1", "Universal rocket module", "ballistic missile", "liquid rocket engine"]
        found_terms = [term for term in glossary_terms if term.lower() in translated.lower()]
        
        if found_terms:
            print(f"\n✅ Найдены термины из глоссария в переводе: {found_terms}")
        else:
            print(f"\n⚠️  Термины из глоссария не найдены в переводе")
            print(f"   Искали: {glossary_terms}")
        
    except Exception as e:
        print(f"❌ Ошибка при переводе: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Тест завершен")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_translation_with_glossary())

