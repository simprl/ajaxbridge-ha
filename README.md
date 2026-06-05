# Ajaxbridge Home Assistant Integration

Custom Home Assistant integration for connecting Home Assistant to an
Ajaxbridge cloud bridge server.

Ajaxbridge receives Ajax Enterprise API / AWS SQS events on a backend server and
streams normalized entity updates to Home Assistant over HTTPS/WebSocket. This
integration is intended for HA operators who receive an installation ID and
installation token from an Ajaxbridge administrator, but do not have access to
the Ajaxbridge admin UI.

## Contents

- [English](#english)
- [Українською](#українською)

## English

### Get Installation Credentials

Before adding the integration, contact the iLazyHome operator through the
contacts on `https://ilazyhome.com/` and request Ajaxbridge access for your Home
Assistant installation.

The operator should provide:

- `Installation ID`;
- one-time installation `API token`;
- bridge URL, usually `https://ajaxbridge.ilazyhome.com`.

Do not use an Ajaxbridge admin token in Home Assistant.

Before hub verification, the target Ajax hub must include the iLazyHome Ajax
user:

```text
ajaxpro@ilazyhome.com
```

The bridge receives Ajax events through this Ajax user, so a hub that does not
share access with this user may not produce events for Ajaxbridge.

By inviting this user, you agree that the iLazyHome Ajax account can receive
events and notifications from this hub so Ajaxbridge can forward the hub state
to your Home Assistant installation. Do not grant this user admin access or
full system control. After the invite is active, open this user's settings in
the Ajax app and leave only the minimum `View notifications` / notification
feed access required for event delivery. Disable other available rights such as
arming control, Night mode, panic button, cameras, automation devices, devices
and rooms, and system settings/configuration access.

To see Ajax hub state in Home Assistant, three things must be true:

1. Home Assistant is connected to Ajaxbridge with the correct installation ID
   and token.
2. The target Ajax hub is shared with `ajaxpro@ilazyhome.com` in the Ajax app.
3. The hub is verified and added to this Home Assistant installation through
   the Ajaxbridge integration flow.

### Install Through HACS

1. Open Home Assistant.
2. Go to `HACS -> Integrations`.
3. Open the menu and choose `Custom repositories`.
4. Add this repository URL with category `Integration`.
5. Download `Ajaxbridge`.
6. Restart Home Assistant.
7. Add `Ajaxbridge` from `Settings -> Devices & services`.

### Connect Home Assistant To Ajaxbridge

The config flow asks for:

- `Bridge URL`: for example `https://ajaxbridge.ilazyhome.com`;
- `Installation ID`: the ID given by the Ajaxbridge operator;
- `API token`: the one-time installation token given by the Ajaxbridge
  operator.

The installation token is not the backend admin token. Do not paste an
Ajaxbridge admin token into Home Assistant.

Connection settings can be changed later from:

```text
Settings -> Devices & services -> Ajaxbridge -> Configure
```

When updating the token, the token field is intentionally shown empty. Enter a
new token only when the operator has regenerated it for this installation.

### Add an Ajax Hub To Home Assistant

Use this flow when an Ajaxbridge operator has already created the HA
installation and given you a valid installation token.

1. Open `Settings -> Devices & services -> Ajaxbridge -> Configure`.
2. Choose `Add hub`.
3. Enter the Ajax hub ID.
4. Home Assistant shows a verification code like `AJB-123456`. Keep this page
   open or copy the code.
5. Open the Ajax app on your phone or desktop.
6. Select the space that contains the target hub.
7. Open the space settings, usually with the gear/settings icon.
8. Open `Users`.
9. Click `Send invites`.
10. Enter:

   ```text
   ajaxpro@ilazyhome.com
   ```

11. Click `Continue` to send the invite.
12. Wait until this user appears in `Active users`, or ask the iLazyHome
    operator to accept/confirm the invite if it remains in `Pending invites`.
13. Open the `ajaxpro@ilazyhome.com` user settings in the Ajax app.
14. Remove unnecessary permissions. Keep `View notifications` / notification
    feed access enabled, but do not grant admin rights,
    settings/configuration access, arming control, camera access, automation
    control, or other permissions that are not required for receiving events.
15. In the Ajax app, open the main menu, then `Account`, then `Edit Account`.
16. Add the verification code to your own Ajax user name. For example, change
    `John Smith` to `John Smith AJB-123456`.
17. Save the account name.
18. Perform a real Ajax action on the target hub, for example arm or disarm a
    group.
19. Return to Home Assistant and choose `Verify hub`.
20. After verification succeeds, choose `Add to installation`.
21. Remove the `AJB-123456` code from your Ajax user name.
22. Check that the hub appears under Ajaxbridge devices and that its entities
   update after a real Ajax arm/disarm event.

The verification code proves that the HA operator can influence the target Ajax
hub through Ajax itself. Knowing only a hub ID is not enough to attach a hub.

The Ajax user invitation flow follows Ajax Systems' official flow:
`Open Ajax app -> select space -> space settings -> Users -> Send invites ->
enter email -> Continue`.

Official Ajax reference:
`https://support.ajax.systems/en/faqs/how-to-invite-users/`.

Official Ajax access-rights reference:
`https://support.ajax.systems/en/faqs/access-settings/`.

If you do not see `Users` or `Send invites` in the Ajax app, your Ajax account
does not have enough rights to invite users. Ask the Ajax space administrator
or the iLazyHome operator to invite `ajaxpro@ilazyhome.com` to the target hub.

If the installation has reached its enabled hub limit, Home Assistant will show
a capacity error. Disable another membership or ask the Ajaxbridge operator to
increase the installation limit.

### Enable Or Disable Existing Hub Memberships

Use:

```text
Settings -> Devices & services -> Ajaxbridge -> Configure
```

Then choose `Enable/disable membership`.

Disabling a membership removes that hub from the active HA state model for this
installation. It does not delete the membership from the Ajaxbridge backend and
does not affect the same hub in other HA installations. Enabling a membership
adds it back if the installation has available hub capacity.

### Expected Home Assistant Entities

Ajaxbridge creates one HA device for each Ajax hub. Ajax security groups are
represented as entities attached to the hub device, not as separate HA devices.

For each Ajax security group:

- `alarm_control_panel.ajax_<hub>_<group>`: source of truth for group armed
  state.
- `binary_sensor.ajax_<hub>_<group>_alarm_active`: active alarm indicator,
  using `device_class=problem`.
- `sensor.ajax_<hub>_<group>_alarm_source`: latest alarm source and event
  details.
- `sensor.ajax_<hub>_<group>_security_state`: readable security state for the
  group.
- `sensor.ajax_<hub>_<group>_last_event`: latest event observed for the group.

For each Ajax hub:

- `sensor.ajax_<hub>_security_summary`: aggregate state across all known
  groups, such as `all_disarmed`, `partially_armed`, `all_armed`, or `unknown`.
- `sensor.ajax_<hub>_delivery_lag`: event delivery lag for diagnostics.

For the integration:

- `sensor.ajaxbridge_diagnostics`: HA-side REST/WebSocket health counters.

There is no hub-level `alarm_control_panel`. A hub can contain multiple groups
with mixed armed/disarmed states, so group-level alarm panels are the security
source of truth.

Room and device objects are currently exposed through event attributes only.
They are not created as persistent HA entities yet.

### Diagnostics

Open `Developer tools -> States` and inspect:

```text
sensor.ajaxbridge_diagnostics
```

Useful attributes:

- `ws_connected`: whether the live WebSocket is connected.
- `ws_last_error`: last WebSocket error, if any.
- `ws_messages`: received WebSocket messages.
- `ws_entity_state_applied`: entity updates applied from WebSocket events.
- `rest_refreshes`: full state-model refresh count.
- `rest_last_state_seq`: latest bridge state sequence received over REST.

If entities stop updating:

1. Check that `sensor.ajaxbridge_diagnostics` is `connected`.
2. Check that `ws_connected` is `true`.
3. Perform a real Ajax action and confirm the group alarm panel or last-event
   sensor changes.
4. Reload the Ajaxbridge integration.
5. Restart Home Assistant only after a custom integration update or if reload
   does not apply changed Python code.

### Troubleshooting

If a newly added hub shows only these two entities:

```text
sensor.ajax_<hub>_security_summary
sensor.ajax_<hub>_delivery_lag
```

reload the Ajaxbridge integration from `Settings -> Devices & services`.
Those two sensors are hub-level aggregate/diagnostic entities. Group-level
alarm panels and group sensors appear after Home Assistant receives a state
model that includes Ajax group metadata for that hub.

If group-level entities still do not appear after reload:

1. Confirm the hub was added to the installation, not only verified.
2. Confirm `ajaxpro@ilazyhome.com` is active on the Ajax hub and can receive
   notifications.
3. Perform a real Ajax arm/disarm action on the target group.
4. Check `sensor.ajaxbridge_diagnostics` and confirm `rest_refreshes` increases
   after reload and `ws_connected` is `true`.
5. Contact the iLazyHome operator if the hub was just added and still has no
   group metadata on the bridge.

## Українською

### Отримання даних для підключення

Перед додаванням інтеграції зв'яжіться з оператором iLazyHome через контакти
на сайті `https://ilazyhome.com/` і попросіть надати доступ Ajaxbridge для вашої
інсталяції Home Assistant.

Оператор має надати:

- `Installation ID`;
- одноразовий `API token` інсталяції;
- bridge URL, зазвичай `https://ajaxbridge.ilazyhome.com`.

Не використовуйте адмінський токен Ajaxbridge у Home Assistant.

Перед перевіркою хаба цільовий Ajax-хаб має містити Ajax-користувача iLazyHome:

```text
ajaxpro@ilazyhome.com
```

Bridge отримує Ajax-події через цього Ajax-користувача, тому хаб без доступу
для цього користувача може не надсилати події в Ajaxbridge.

Запрошуючи цього користувача, ви погоджуєтеся, що Ajax-акаунт iLazyHome може
отримувати події та нотифікації з цього хаба, щоб Ajaxbridge міг передавати
стан хаба у вашу інсталяцію Home Assistant. Не надавайте цьому користувачу
admin-доступ або повний контроль системи. Після активації запрошення відкрийте
налаштування цього користувача в застосунку Ajax і залиште тільки мінімальний
доступ `View notifications` / notification feed, потрібний для доставки подій.
Вимкніть інші доступні права: керування охороною, Night mode, panic button,
камери, automation devices, devices and rooms, а також доступ до system
settings/configuration.

Щоб стан Ajax-хаба з'явився в Home Assistant, мають виконуватися три умови:

1. Home Assistant підключений до Ajaxbridge з правильним installation ID і
   token.
2. Цільовий Ajax-хаб відкритий для `ajaxpro@ilazyhome.com` у застосунку Ajax.
3. Хаб перевірений і доданий до цієї інсталяції Home Assistant через flow
   інтеграції Ajaxbridge.

### Встановлення через HACS

1. Відкрийте Home Assistant.
2. Перейдіть до `HACS -> Integrations`.
3. Відкрийте меню і виберіть `Custom repositories`.
4. Додайте URL цього репозиторію з категорією `Integration`.
5. Завантажте `Ajaxbridge`.
6. Перезапустіть Home Assistant.
7. Додайте `Ajaxbridge` у `Settings -> Devices & services`.

### Підключення Home Assistant до Ajaxbridge

Форма налаштування запитує:

- `Bridge URL`: наприклад `https://ajaxbridge.ilazyhome.com`;
- `Installation ID`: ідентифікатор інсталяції, який надав оператор
  Ajaxbridge;
- `API token`: одноразовий токен інсталяції, який надав оператор Ajaxbridge.

Токен інсталяції не є адмінським токеном backend. Не вводьте адмінський токен
Ajaxbridge у Home Assistant.

Параметри підключення можна змінити пізніше тут:

```text
Settings -> Devices & services -> Ajaxbridge -> Configure
```

Під час оновлення токена поле токена навмисно показується порожнім. Вводьте
новий токен тільки тоді, коли оператор згенерував його для цієї інсталяції.

### Додавання Ajax-хаба до Home Assistant

Використовуйте цей сценарій, коли оператор Ajaxbridge вже створив HA
інсталяцію і надав чинний токен інсталяції.

1. Відкрийте `Settings -> Devices & services -> Ajaxbridge -> Configure`.
2. Виберіть `Add hub`.
3. Введіть ID Ajax-хаба.
4. Home Assistant покаже код перевірки на кшталт `AJB-123456`. Залиште цю
   сторінку відкритою або скопіюйте код.
5. Відкрийте застосунок Ajax на телефоні або комп'ютері.
6. Виберіть space, у якому знаходиться цільовий хаб.
7. Відкрийте settings цього space, зазвичай через іконку шестерні/settings.
8. Відкрийте `Users`.
9. Натисніть `Send invites`.
10. Введіть:

   ```text
   ajaxpro@ilazyhome.com
   ```

11. Натисніть `Continue`, щоб надіслати запрошення.
12. Дочекайтеся, поки цей користувач з'явиться в `Active users`, або попросіть
    оператора iLazyHome прийняти/підтвердити запрошення, якщо воно залишилося в
    `Pending invites`.
13. Відкрийте налаштування користувача `ajaxpro@ilazyhome.com` у застосунку
    Ajax.
14. Приберіть зайві права. Залиште доступ `View notifications` / notification
    feed увімкненим, але не надавайте admin rights,
    settings/configuration access, arming control, camera access, automation
    control або інші права, які не потрібні для отримання подій.
15. У застосунку Ajax відкрийте головне меню, потім `Account`, потім
    `Edit Account`.
16. Додайте код перевірки до імені вашого Ajax-користувача. Наприклад, змініть
    `John Smith` на `John Smith AJB-123456`.
17. Збережіть ім'я акаунта.
18. Виконайте реальну дію в Ajax на цільовому хабі, наприклад поставте групу під
   охорону або зніміть її з охорони.
19. Поверніться в Home Assistant і виберіть `Verify hub`.
20. Після успішної перевірки виберіть `Add to installation`.
21. Видаліть код `AJB-123456` з імені вашого Ajax-користувача.
22. Переконайтеся, що хаб з'явився серед пристроїв Ajaxbridge і що його сутності
   оновлюються після реальної Ajax-дії.

Код перевірки підтверджує, що оператор HA може впливати на цільовий Ajax-хаб
через сам Ajax. Одного знання ID хаба недостатньо, щоб прив'язати хаб.

Flow запрошення користувача відповідає офіційній інструкції Ajax Systems:
`Open Ajax app -> select space -> space settings -> Users -> Send invites ->
enter email -> Continue`.

Офіційна інструкція Ajax:
`https://support.ajax.systems/en/faqs/how-to-invite-users/`.

Офіційна інструкція Ajax щодо обмеження доступу:
`https://support.ajax.systems/en/faqs/access-settings/`.

Якщо ви не бачите `Users` або `Send invites` у застосунку Ajax, ваш Ajax-акаунт
не має достатніх прав для запрошення користувачів. Попросіть адміністратора
Ajax space або оператора iLazyHome запросити `ajaxpro@ilazyhome.com` на
цільовий хаб.

Якщо інсталяція досягла ліміту увімкнених хабів, Home Assistant покаже помилку
місткості. Вимкніть інше membership або попросіть оператора Ajaxbridge
збільшити ліміт інсталяції.

### Увімкнення або вимкнення існуючих memberships

Відкрийте:

```text
Settings -> Devices & services -> Ajaxbridge -> Configure
```

Потім виберіть `Enable/disable membership`.

Вимкнення membership прибирає цей хаб з активної state model для цієї
інсталяції HA. Це не видаляє membership з backend Ajaxbridge і не впливає на
той самий хаб в інших HA-інсталяціях. Увімкнення membership додає хаб назад,
якщо в інсталяції є вільний ліміт хабів.

### Очікувані сутності Home Assistant

Ajaxbridge створює один HA device для кожного Ajax-хаба. Ajax security groups
представлені як сутності всередині device хаба, а не як окремі HA devices.

Для кожної Ajax security group:

- `alarm_control_panel.ajax_<hub>_<group>`: основне джерело стану охорони
  групи.
- `binary_sensor.ajax_<hub>_<group>_alarm_active`: індикатор активної тривоги,
  з `device_class=problem`.
- `sensor.ajax_<hub>_<group>_alarm_source`: останнє джерело тривоги і деталі
  події.
- `sensor.ajax_<hub>_<group>_security_state`: читабельний стан охорони групи.
- `sensor.ajax_<hub>_<group>_last_event`: остання подія для групи.

Для кожного Ajax-хаба:

- `sensor.ajax_<hub>_security_summary`: агрегований стан усіх відомих груп,
  наприклад `all_disarmed`, `partially_armed`, `all_armed` або `unknown`.
- `sensor.ajax_<hub>_delivery_lag`: затримка доставки подій для діагностики.

Для інтеграції:

- `sensor.ajaxbridge_diagnostics`: HA-side лічильники стану REST/WebSocket.

Hub-level `alarm_control_panel` не створюється. Один хаб може містити кілька
груп з різними станами охорони, тому джерелом правди є group-level alarm
panels.

Rooms і devices поки доступні тільки як атрибути подій. Вони ще не створюються
як постійні HA entities.

### Діагностика

Відкрийте `Developer tools -> States` і перегляньте:

```text
sensor.ajaxbridge_diagnostics
```

Корисні атрибути:

- `ws_connected`: чи підключений live WebSocket.
- `ws_last_error`: остання помилка WebSocket, якщо вона була.
- `ws_messages`: отримані WebSocket-повідомлення.
- `ws_entity_state_applied`: оновлення сутностей, застосовані з WebSocket.
- `rest_refreshes`: кількість повних REST-оновлень state model.
- `rest_last_state_seq`: останній bridge state sequence, отриманий через REST.

Якщо сутності перестали оновлюватися:

1. Перевірте, що `sensor.ajaxbridge_diagnostics` має стан `connected`.
2. Перевірте, що `ws_connected` дорівнює `true`.
3. Виконайте реальну Ajax-дію і переконайтеся, що group alarm panel або
   last-event sensor змінився.
4. Перезавантажте інтеграцію Ajaxbridge.
5. Перезапускайте Home Assistant тільки після оновлення custom integration або
   якщо reload не застосував змінений Python-код.

### Вирішення проблем

Якщо щойно доданий хаб показує тільки дві сутності:

```text
sensor.ajax_<hub>_security_summary
sensor.ajax_<hub>_delivery_lag
```

перезавантажте інтеграцію Ajaxbridge у `Settings -> Devices & services`.
Ці дві сутності є hub-level агрегатом і діагностикою. Group-level alarm panels
та сенсори груп з'являються після того, як Home Assistant отримає state model
з Ajax group metadata для цього хаба.

Якщо group-level сутності не з'явилися після reload:

1. Переконайтеся, що хаб додано до інсталяції, а не тільки перевірено.
2. Переконайтеся, що `ajaxpro@ilazyhome.com` активний на Ajax-хабі і може
   отримувати нотифікації.
3. Виконайте реальну Ajax-дію arm/disarm на цільовій групі.
4. Перевірте `sensor.ajaxbridge_diagnostics`: `rest_refreshes` має збільшитися
   після reload, а `ws_connected` має бути `true`.
5. Зв'яжіться з оператором iLazyHome, якщо хаб щойно додано і на bridge все ще
   немає group metadata для нього.
