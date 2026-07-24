from typing import Dict, Any

TEXTS: Dict[str, Dict[str, str]] = {
    "ru": {
        # Главное меню подписчика
        "sub_menu_header": "📢 **Предложка канала {channel_title}**\n{rating_str}\nВыберите действие ниже:",
        "rating_line": "⭐ **Рейтинг:** {avg_rating} / 5.0 ({count} оценок)\n",
        "btn_idea": "💡 Предложить идею",
        "btn_question_all": "❓ Задать вопрос владельцам",
        "btn_question_admin": "👤 Вопрос конкретному админу",
        "btn_review": "⭐ Оставить отзыв и оценку",

        # Выбор анонимности
        "choose_anonymity": "Как вы хотите отправить сообщение?",
        "btn_anon": "🕵️ Анонимно",
        "btn_public": "👤 Открыто (@{username})",

        # Промпты для ввода
        "prompt_send_idea": "💡 Напишите вашу идею или отправьте медиафайл (фото/видео/голосовое):",
        "prompt_send_question": "❓ Напишите ваш вопрос (можно прикрепить медиафайл):",
        "prompt_select_rating": "⭐ Выберите вашу оценку каналу от 1 до 5 звезд:",
        "prompt_send_review_text": "✍️ Напишите краткий комментарий к вашей оценке (или нажмите «Пропустить»):",
        "btn_skip": "⏩ Пропустить",

        # Уведомления подписчику
        "msg_sent_success": "✅ Ваше сообщение успешно отправлено администраторам!",
        "review_saved_success": "🎉 Спасибо за ваш отзыв! Оценка сохранена.",
        "review_cooldown_error": "⏳ Вы уже оставляли отзыв. Изменить его можно будет через {days_left} дн.",
        "user_banned_error": "🛑 Администрация канала ограничила вам доступ к отправке сообщений.",

        # Уведомления админу в ЛС
        "admin_new_idea": "📥 **Новая идея для канала [{channel_title}]**\n👤 **Автор:** {sender_info}\n\n💬 {text}",
        "admin_new_question": "📥 **Новый вопрос для канала [{channel_title}]**\n👤 **Автор:** {sender_info}\n📌 **Кому:** {target_info}\n\n💬 {text}",
        "admin_new_review": "⭐ **Новый отзыв для канала [{channel_title}]**\nОценка: {stars}\n💬 Comment: {text}",

        # Кнопки для админа в карточке сообщения
        "btn_reply_private": "💬 Ответить лично",
        "btn_reply_public": "📢 Публичный ответ в канал",
        "btn_publish_idea": "🚀 Опубликовать в канал",
        "btn_ban_user": "🚫 Заблокировать",
        "btn_unban_user": "🔄 Разблокировать",

        # Шаблон поста в канале (Публичный ответ)
        "channel_public_reply": "❓ **Вопрос от подписчика:** {sender_str}\n*«{question_text}»*\n\n💬 **Ответ:**\n*«{reply_text}»*\n\n🤖 *Задать вопрос или предложить идею: {bot_link}*",
        "channel_public_idea": "💡 **Идея от подписчика:** {sender_str}\n\n{idea_text}\n\n🤖 *Предложить свою идею: {bot_link}*",

        # Админ Панель
        "admin_panel_welcome": "⚙️ **Панель управления Onward**\nВыберите канал для настройки:",
        "btn_my_channels": "📢 Мои каналы",
        "btn_channel_settings": "⚙️ Настройки кнопок",
        "btn_my_profile_settings": "👤 Мой профиль админа",
        "btn_get_link": "🔗 Получить ссылку предложки",
        "btn_invite_coadmin": "👥 Добавить со-админа",
        "btn_premium": "⭐ Onward Premium",
        "btn_language": "🌐 Язык / Language",
    },

    "en": {
        "sub_menu_header": "📢 **Suggestion box for {channel_title}**\n{rating_str}\nChoose an action below:",
        "rating_line": "⭐ **Rating:** {avg_rating} / 5.0 ({count} reviews)\n",
        "btn_idea": "💡 Suggest an idea",
        "btn_question_all": "❓ Ask channel owners",
        "btn_question_admin": "👤 Ask specific admin",
        "btn_review": "⭐ Leave review & rating",

        "choose_anonymity": "How would you like to send this message?",
        "btn_anon": "🕵️ Anonymously",
        "btn_public": "👤 Publicly (@{username})",

        "prompt_send_idea": "💡 Type your idea or send media (photo/video/voice):",
        "prompt_send_question": "❓ Type your question (media attachments supported):",
        "prompt_select_rating": "⭐ Rate the channel from 1 to 5 stars:",
        "prompt_send_review_text": "✍️ Write a short comment (or tap Skip):",
        "btn_skip": "⏩ Skip",

        "msg_sent_success": "✅ Your message has been sent to the admins!",
        "review_saved_success": "🎉 Thank you for your review!",
        "review_cooldown_error": "⏳ You have already left a review. You can update it in {days_left} days.",
        "user_banned_error": "🛑 The channel administration has restricted you from sending messages.",

        "admin_new_idea": "📥 **New idea for [{channel_title}]**\n👤 **Author:** {sender_info}\n\n💬 {text}",
        "admin_new_question": "📥 **New question for [{channel_title}]**\n👤 **Author:** {sender_info}\n📌 **To:** {target_info}\n\n💬 {text}",
        "admin_new_review": "⭐ **New review for [{channel_title}]**\nRating: {stars}\n💬 Comment: {text}",

        "btn_reply_private": "💬 Reply privately",
        "btn_reply_public": "📢 Post reply to channel",
        "btn_publish_idea": "🚀 Publish to channel",
        "btn_ban_user": "🚫 Ban user",
        "btn_unban_user": "🔄 Unban user",

        "channel_public_reply": "❓ **Question from subscriber:** {sender_str}\n*«{question_text}»*\n\n💬 **Answer:**\n*«{reply_text}»*\n\n🤖 *Ask a question: {bot_link}*",
        "channel_public_idea": "💡 **Idea from subscriber:** {sender_str}\n\n{idea_text}\n\n🤖 *Suggest an idea: {bot_link}*",

        "admin_panel_welcome": "⚙️ **Onward Control Panel**\nSelect a channel to configure:",
        "btn_my_channels": "📢 My channels",
        "btn_channel_settings": "⚙️ Button settings",
        "btn_my_profile_settings": "👤 My admin profile",
        "btn_get_link": "🔗 Get suggestion link",
        "btn_invite_coadmin": "👥 Add co-admin",
        "btn_premium": "⭐ Onward Premium",
        "btn_language": "🌐 Language",
    },

    "hi": {
        "sub_menu_header": "📢 **канал के लिए सुझाव पेटी {channel_title}**\n{rating_str}\nनीचे एक विकल्प चुनें:",
        "rating_line": "⭐ **रेटिंग:** {avg_rating} / 5.0 ({count} समीक्षाएं)\n",
        "btn_idea": "💡 विचार सुझाव दें",
        "btn_question_all": "❓ मालिकों से सवाल पूछें",
        "btn_question_admin": "👤 विशिष्ट एडमिन से पूछें",
        "btn_review": "⭐ समीक्षा और रेटिंग दें",
        "choose_anonymity": "आप यह संदेश कैसे भेजना चाहते हैं?",
        "btn_anon": "🕵️ गुमनाम (Anonymous)",
        "btn_public": "👤 सार्वजनिक (@{username})",
        "prompt_send_idea": "💡 अपना विचार लिखें या मीडिया भेजें:",
        "prompt_send_question": "❓ अपना प्रश्न लिखें:",
        "prompt_select_rating": "⭐ 1 से 5 स्टार तक रेट करें:",
        "prompt_send_review_text": "✍️ एक टिप्पणी लिखें (या स्किप करें):",
        "btn_skip": "⏩ छोड़ें (Skip)",
        "msg_sent_success": "✅ आपका संदेश एडमिन को भेज दिया गया है!",
        "review_saved_success": "🎉 आपकी समीक्षा के लिए धन्यवाद!",
        "review_cooldown_error": "⏳ आप पहले ही समीक्षा दे चुके हैं। {days_left} दिनों में अपडेट कर सकते हैं।",
        "user_banned_error": "🛑 एडमिन ने आपको संदेश भेजने से प्रतिबंधित कर दिया है।",
        "btn_reply_private": "💬 निजी उत्तर दें",
        "btn_reply_public": "📢 चैनल पर उत्तर दें",
        "btn_publish_idea": "🚀 चैनल में प्रकाशित करें",
        "btn_ban_user": "🚫 ब्लॉक करें",
        "btn_unban_user": "🔄 अनब्लॉक करें",
        "admin_panel_welcome": "⚙️ **Onward कंट्रोल पैनल**",
        "btn_my_channels": "📢 मेरे चैनल",
        "btn_channel_settings": "⚙️ बटन सेटिंग्स",
        "btn_my_profile_settings": "👤 मेरी एडमिन प्रोफाइल",
        "btn_get_link": "🔗 लिंक प्राप्त करें",
        "btn_invite_coadmin": "👥 एडमिन जोड़ें",
        "btn_premium": "⭐ Onward प्रीमियम",
        "btn_language": "🌐 भाषा (Language)",
    },

    "es": {
        "sub_menu_header": "📢 **Sugerencias para {channel_title}**\n{rating_str}\nElige una opción:",
        "rating_line": "⭐ **Calificación:** {avg_rating} / 5.0 ({count} reseñas)\n",
        "btn_idea": "💡 Sugerir una idea",
        "btn_question_all": "❓ Preguntar a los dueños",
        "btn_question_admin": "👤 Preguntar a un admin",
        "btn_review": "⭐ Dejar reseña y valoración",
        "choose_anonymity": "¿Cómo quieres enviar este mensaje?",
        "btn_anon": "🕵️ Anónimo",
        "btn_public": "👤 Público (@{username})",
        "prompt_send_idea": "💡 Escribe tu idea o envía contenido multimedia:",
        "prompt_send_question": "❓ Escribe tu pregunta:",
        "prompt_select_rating": "⭐ Califica el canal de 1 a 5 estrellas:",
        "prompt_send_review_text": "✍️ Escribe un comentario corto (o pulsa Omitir):",
        "btn_skip": "⏩ Omitir",
        "msg_sent_success": "✅ ¡Tu mensaje ha sido enviado a los administradores!",
        "review_saved_success": "🎉 ¡Gracias por tu reseña!",
        "review_cooldown_error": "⏳ Ya dejaste una reseña. Podrás actualizarla en {days_left} días.",
        "user_banned_error": "🛑 La administración te ha restringido el envío de mensajes.",
        "btn_reply_private": "💬 Responder en privado",
        "btn_reply_public": "📢 Publicar respuesta en canal",
        "btn_publish_idea": "🚀 Publicar en el canal",
        "btn_ban_user": "🚫 Bloquear usuario",
        "btn_unban_user": "🔄 Desbloquear",
        "admin_panel_welcome": "⚙️ **Panel de control Onward**",
        "btn_my_channels": "📢 Mis canales",
        "btn_channel_settings": "⚙️ Ajustes de botones",
        "btn_my_profile_settings": "👤 Mi perfil de admin",
        "btn_get_link": "🔗 Obtener enlace",
        "btn_invite_coadmin": "👥 Añadir co-admin",
        "btn_premium": "⭐ Onward Premium",
        "btn_language": "🌐 Idioma",
    }
}


def t(key: str, lang: str = "ru", **kwargs) -> str:
    """
    Получить локализованный текст по ключу.
    Если языка нет — используется 'en'. Если ключа нет в языке — возвращает сам ключ.
    """
    lang_dict = TEXTS.get(lang, TEXTS["en"])
    text_template = lang_dict.get(key) or TEXTS["en"].get(key, key)

    if kwargs:
        try:
            return text_template.format(**kwargs)
        except KeyError:
            return text_template

    return text_template