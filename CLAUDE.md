# DD Офис — Проектная память

## Продукт
**DD Офис** — PWA-приложение для Due Diligence анализа.  
URL: https://rakhimkadyrov-collab.github.io/diagnostika/  
Репозиторий: `rakhimkadyrov-collab/diagnostika`  
Ветка разработки: `claude/dd-office-app-chat-1bk322`  
Файл приложения: `index.html` (единственный файл, ~1385 строк)

## Ключевые технические детали

### API-вызовы (КРИТИЧНО)
Заголовок для браузерных запросов к Anthropic: `anthropic-dangerous-direct-browser-access: 'true'`  
(НЕ `anthropic-dangerous-allow-browser` — это неверный вариант!)

Функция с fallback через corsproxy.io:
```javascript
async function claudeFetch(key, body) {
  const direct = 'https://api.anthropic.com/v1/messages';
  const proxy  = 'https://corsproxy.io/?url=' + encodeURIComponent(direct);
  const headers = {
    'x-api-key': key,
    'anthropic-version': '2023-06-01',
    'anthropic-dangerous-direct-browser-access': 'true',
    'content-type': 'application/json'
  };
  try {
    const res = await fetch(direct, { method: 'POST', headers, body });
    if (res.status !== 0) return res;
  } catch (_) {}
  return fetch(proxy, { method: 'POST', headers, body });
}
```

### Notion
- Projects DB: `ab8e71adc1c74031aeee11aaf34869fe`
- Conclusions DB: `c5d4665c72a24ba2b588827f5d2ad75f`
- Родительская страница DD Офис: `38084664-2423-8181-b307-db606ac0180a`
- Notion API роутится через `corsproxy.io` (браузер не может напрямую)

### 8 агентов (последовательный конвейер)
1. `marketer` — TAM/SAM/SOM, прогноз выручки
2. `financier` — верификация + DCF/EV·EBITDA/M&A оценка
3. `auditor` — качество учёта, скрытые обязательства
4. `lawyer` — корп. структура, CoC риски, структура сделки
5. `tax` — ТЦО, СИДН, PPT-тест, налоговый хвост
6. `specialist` — операционная реальность, capex-gap
7. `risk` — матрица рисков (вероятность × ущерб), walk-away триггеры
8. `ceo` — синтез всех 7 агентов, финальный вердикт + целевая цена

Каждый последующий агент получает выводы предыдущих в системном промпте.

### localStorage
- Проекты: ключ `dd-office-v2`
- Настройки (API ключи): ключ `dd-office-settings-v2`

### Деплой
GitHub Actions: `.github/workflows/pages.yml` — auto-deploy при push в ветку `claude/dd-office-app-chat-1bk322`

---

## Инструкция пользователя и администратора

*(Сохранена в Notion: https://app.notion.com/p/381846642423813bad17f8413663ca83)*

### Для пользователя

**Первый запуск:**
1. Открыть https://rakhimkadyrov-collab.github.io/diagnostika/
2. Нажать "⚙ Настройки", ввести Claude API Key и (опционально) Notion Integration Token
3. Нажать "Сохранить" — ключи хранятся локально в браузере

**Создание проекта DD:**
1. Нажать "+ Новый проект"
2. Шаг 1 — заполнить название компании, отрасль, тип сделки, описание
3. Шаг 2 — загрузить файлы (PDF, Excel, Word, TXT) — можно несколько
4. Нажать "Запустить анализ" — 8 агентов запускаются последовательно
5. Каждый агент показывает прогресс; финальный агент CEO даёт итоговый вердикт

**Просмотр результатов:**
- Вкладка "Обзор" — краткое резюме проекта
- Вкладка "Агенты" — полные выводы каждого из 8 агентов
- Вкладка "Отчёт" — консолидированный отчёт, кнопки "Печать" и "Сохранить в Notion"

**Печать отчёта:**
- Кнопка "Распечатать" — открывает новое окно с профессиональным HTML-отчётом (navy-шапка, Times New Roman)
- Использовать Ctrl+P / Cmd+P в браузере, сохранять как PDF

**Сохранение в Notion:**
- Кнопка "Сохранить в Notion" — требует заполненного Notion Token в настройках
- Создаёт запись в базе проектов и отдельные записи по каждому агенту

### Для администратора

**Обновление кода:**
1. Редактировать `/home/user/diagnostika/index.html`
2. `git add index.html && git commit -m "описание" && git push -u origin claude/dd-office-app-chat-1bk322`
3. GitHub Actions автоматически деплоит за ~1-2 минуты

**Настройка Notion:**
1. Создать Integration на https://www.notion.so/my-integrations
2. Дать интеграции доступ к страницам DD Офис и обеим базам данных
3. Скопировать "Internal Integration Token" в настройки приложения

**Настройка Claude API:**
1. Получить ключ на https://console.anthropic.com
2. Убедиться, что включён план с доступом к `claude-sonnet-4-6`
3. Ввести ключ в настройки приложения

**Мониторинг деплоя:**
- GitHub Actions: https://github.com/rakhimkadyrov-collab/diagnostika/actions
- Логи GitHub Pages: Settings → Pages в репозитории

**Смена модели:**
- В настройках приложения выбрать модель (claude-sonnet-4-6, claude-opus-4-8, etc.)
- Разные модели = разная стоимость и качество анализа

**Структура Notion (базы данных):**
- `ab8e71adc1c74031aeee11aaf34869fe` — Projects (основная база проектов)
- `c5d4665c72a24ba2b588827f5d2ad75f` — Conclusions (выводы агентов)

**Безопасность:**
- Claude API Key и Notion Token хранятся ТОЛЬКО в localStorage пользователя
- Ключи не передаются на серверы приложения (сервера нет — это статический сайт)
- При смене устройства/браузера нужно заново вводить ключи
- Для команды: каждый пользователь вводит свои ключи
