import type { Course, Section } from '../types'

// Course 9 — Catch card fraud (silver → ml → gold). Every section is a workspace run
// (spine/detect/): the rule and the features run on serverless; the model is trained and scored on
// the laptop with scikit-learn, tracked in MLflow and registered in Unity Catalog. Labels are
// September's chargebacks only.
const s = (id: string, title: string, scene: string, narration: string): Section => ({ id, title, scene, narration })

export const detect: Course = {
  id: 'detect',
  title: 'Catch card fraud',
  sections: [
    s('card-testing', 'What card testing looks like', 'detect-card-testing',
      "Before fraudsters spend a stolen card number, they test it. They try tiny amounts, a euro or two, at online shops the card has never used, many times in a few minutes, usually at night, to find out which numbers still work. It is called card testing, and it leaves a pattern a bank can see. Ring dot py, in the editor, looks for it in silver card transactions on one night, the twenty second of October: authorizations before five in the morning, grouped by card, keeping the cards with more than three. Six cards come back, and they look nothing like a customer. Each made eleven authorizations, within six to twelve minutes. Together they total only thirteen to sixteen euros. Some were declined, up to seven of eleven, and each card touched eight to eleven different merchants. The last line spells out one card, K003529: eleven authorizations between ten past two and nineteen minutes past, each between fifty six cents and two euros. The plot draws them, one bar per authorization. Nobody buys eleven things worth a euro each at eleven shops in nine minutes. Six cards at the same minutes of the same night is not chance either: it is one ring, testing a batch of numbers. That is what this course will catch, first with a rule, then with a model. And there is one thing we cannot know yet: whether these six were really fraud. That only comes later, as chargebacks."),
    s('rules', 'Rules first', 'detect-rules',
      "The simplest detector is a rule, and banks start there because anyone can read it. Velocity dot sql states one: flag an authorization when its card has made more than five in the last ten minutes. The window function in the editor counts, for every authorization, the same card's authorizations in the ten minutes before it, a range over time, not a number of rows. A rule is only worth what it catches, so the query checks it against the only truth the bank has: September's chargebacks, the transactions cardholders later disputed as fraud. It runs on six nights, each ring's night and the night before it. On the twelfth of September the rule flags twenty eight authorizations, and all twenty eight were fraud. On the twenty sixth, thirty four, all fraud. On the nights before, nothing. So the rule never cried wolf. But each ring made sixty fraudulent authorizations, and the rule caught only about half: a card's first five authorizations in a burst can never be past five. On the twenty second of October it flags thirty six, and the fraud column says zero, not because they are innocent, but because October's chargebacks have not arrived yet. A label always comes late. The side pane shows the rule day by day, and the window it counts. A rule that runs once a day finds a ring the morning after. Next, the same rule, running as the authorizations arrive."),
    s('streaming-rule', 'A streaming rule', 'detect-streaming-rule',
      "TODO"),
    s('features', 'Features in Unity Catalog', 'detect-features',
      "A rule looks at one signal. A model can weigh several, but first they have to be computed, the same way, for every authorization: those are features. Features dot py, in the editor, builds them in one SQL statement over silver, into a table in the ml schema, ml card features. For each authorization: auths ten m, the card's authorizations in the ten minutes before it, the rule's own number. Online, whether the card was not present. Tiny amount, under two euros, the size of a test charge. Night, before five in the morning. And one more column, fraud, the label: whether a chargeback later named this authorization. Only September has labels; October's twenty second is there to be scored, not to learn from. The terminal counts it: eighteen thousand four hundred and eighty rows over six days. On the twelfth of September, six thousand three hundred and forty three authorizations, sixty of them fraud. On the twenty sixth, six thousand three hundred and forty six, sixty fraud. The average velocity is about one: almost every authorization is the only one its card made in ten minutes, which is exactly why the rings stand out. Because the table lives in Unity Catalog, it has an owner, grants and lineage like any other: the side pane lists what each feature means. Next, the model that learns from it."),
    s('mlflow', 'MLflow tracking', 'detect-mlflow', 'TODO'),
    s('registry', 'A model in Unity Catalog', 'detect-registry', 'TODO'),
    s('score', 'Scoring a new day', 'detect-score', 'TODO'),
    s('tradeoff', 'Precision, recall, money', 'detect-tradeoff', 'TODO'),
  ],
}
