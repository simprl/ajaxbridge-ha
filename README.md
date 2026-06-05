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

The target Ajax hub must also include the iLazyHome Ajax user:

```text
ajaxpro@ilazyhome.com
```

Add or invite this user in the Ajax app before starting hub verification. The
bridge receives Ajax events through this Ajax user, so a hub that does not share
access with this user may not produce events for Ajaxbridge.

### Install Through HACS

1. Open Home Assistant.
2. Go to `HACS -> Integrations`.
3. Open the menu and choose `Custom repositories`.
4. Add this repository URL with category `Integration`.
5. Download `Ajaxbridge`.
6. Restart Home Assistant.
7. Add `Ajaxbridge` from `Settings -> Devices & services`.

### Connect Home Assistant

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

### Add a Hub From Home Assistant

Use this flow when an Ajaxbridge operator has already created the HA
installation and given you a valid installation token.

1. Open `Settings -> Devices & services -> Ajaxbridge -> Configure`.
2. Choose `Add hub`.
3. Enter the Ajax hub ID.
4. Home Assistant shows a verification code like `AJB-123456`.
5. Temporarily add that code to your Ajax user name for the target hub.
6. Perform a real Ajax action on that hub, for example arm or disarm a group.
7. Return to Home Assistant and choose `Verify hub`.
8. After verification succeeds, choose `Add to installation`.
9. Check that the hub appears under Ajaxbridge devices and that its entities
   update after a real Ajax arm/disarm event.

The verification code proves that the HA operator can influence the target Ajax
hub through Ajax itself. Knowing only a hub ID is not enough to attach a hub.

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

Цільовий Ajax-хаб також має містити Ajax-користувача iLazyHome:

```text
ajaxpro@ilazyhome.com
```

Додайте або запросіть цього користувача в застосунку Ajax перед перевіркою
хаба. Bridge отримує Ajax-події через цього Ajax-користувача, тому хаб без
доступу для цього користувача може не надсилати події в Ajaxbridge.

### Встановлення через HACS

1. Відкрийте Home Assistant.
2. Перейдіть до `HACS -> Integrations`.
3. Відкрийте меню і виберіть `Custom repositories`.
4. Додайте URL цього репозиторію з категорією `Integration`.
5. Завантажте `Ajaxbridge`.
6. Перезапустіть Home Assistant.
7. Додайте `Ajaxbridge` у `Settings -> Devices & services`.

### Підключення Home Assistant

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

### Додавання хаба з Home Assistant

Використовуйте цей сценарій, коли оператор Ajaxbridge вже створив HA
інсталяцію і надав чинний токен інсталяції.

1. Відкрийте `Settings -> Devices & services -> Ajaxbridge -> Configure`.
2. Виберіть `Add hub`.
3. Введіть ID Ajax-хаба.
4. Home Assistant покаже код перевірки на кшталт `AJB-123456`.
5. Тимчасово додайте цей код до імені вашого Ajax-користувача на цільовому
   хабі.
6. Виконайте реальну дію в Ajax на цьому хабі, наприклад поставте групу під
   охорону або зніміть її з охорони.
7. Поверніться в Home Assistant і виберіть `Verify hub`.
8. Після успішної перевірки виберіть `Add to installation`.
9. Переконайтеся, що хаб з'явився серед пристроїв Ajaxbridge і що його сутності
   оновлюються після реальної Ajax-дії.

Код перевірки підтверджує, що оператор HA може впливати на цільовий Ajax-хаб
через сам Ajax. Одного знання ID хаба недостатньо, щоб прив'язати хаб.

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
