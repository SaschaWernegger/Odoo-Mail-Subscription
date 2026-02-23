# My Mail

## Features
* Considers scheduled reports, bypass check and followers.
* Grouped list displaying toggles to opt out/in and frequencies, in the user form.
* Bulk editing views, accessible via smart button in template/mail
* Category and Group edits in the template form.
* Audit logs


## Assumptions & Challenges

### Frequency
Reports generated with Scheduled Reports (Enterprice), should pass the "mail_schedule_type" int the context, from what i could find out. Immediate seems to be from the field "mail_notify_force_send", so in this case a user will get the mayl from some ui interaction i guess. Other scheduled mails should also pass the frequency in the context as "mail_schedule_type", "immediate" is also supported to be passed in this field or True in mail_notify_force_send.

Supported frequencies:
    * immediate
    * daily
    * weekly
    * monthly

Also it is assumed that multiple frequencies should be selectable, the same template could possibly be sent multiple time. So when type is "informational" or "marketing", when opted out no mails receive, then the indivdual frequencies are opted in again and the final design is quite different.

mail_template.user_mail_subscription_ids -> user_mail_subscription.mail_subscription_frequency -> user_mail_subscription_subscribed_frequency_rel

For now, for "informational", all frequenceis are selected by default, storing an entry for each frequency.

## Subscribtion Policy
To make it extensibel, a UserSubscriptionPolicy class was created. The policy has id, name, description, and sequence and is responsible for filtering the recipients. Using the register_policy decorator the policy can be added to the registry. On first install this also creates the policy data as entries in the table mail_subscription_policy.

mail_template.mail_subscription_policy_id -> mail_subscription_policy

The policy and the template ids are then passed to the context in mail_template.send_mail as 
mail_template_id and mail_template_policy. This determines the policy to use, and instances are retrieved from a registry. The bypass is context-driven: pass bypass_subscription_check=True in context to skip subscription filtering for that send operation.

The default for a policy must be that no entries are present, only storing changes(could also be defined by a policy in the future) and alowing for simple reset functionality. For now also the entries

### Audit of Template
A technical model in Odoo is a model that exists to support the framework itself, not a business workflow.
Tracking is NOT just logging

Odoo tracking (mail.thread) implies:
* Chatter messages
* Followers
* Access rules for posting
* Message subtypes
* Notifications
* Performance overhead

For technical models, this causes real problems.

So for fields on mail_template, custom tracking is needed. Threfore we store entries in mail_message for now(could be done in a separate table).

we store:
* template_group
* subscription_policy_id

### Groupings in a Form
Grouping in a form is not really supported fore relations like one2many. This needs to be solved by creating a custom view.