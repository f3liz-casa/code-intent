/*
 * SPDX-FileCopyrightText: syuilo and misskey-project
 * SPDX-License-Identifier: AGPL-3.0-only
 */

export type EmojiDef = {
	emoji: string;
	name: string;
	url: string;
	aliasOf?: string;
} | {
	emoji: string;
	name: string;
	aliasOf?: string;
	isCustomEmoji?: true;
};
type EmojiScore = { emoji: EmojiDef, score: number };

const AUTOCOMPLETE_POPUP_SIZE = 6;
const FUZZY_MIN_QUERY_LENGTH = 4;

type SearchContext = { query: string; emojiDb: EmojiDef[]; max: number; matches: Map<string, EmojiScore> };
type Step = (context: SearchContext) => void;
type NameTest = (x: EmojiDef, query: string) => boolean;

const originalNameOf = (x: EmojiDef) => x.aliasOf ?? x.name;
const isAlias = (x: EmojiDef) => Boolean(x.aliasOf);

function setScore(bonus: number, isMatch: NameTest): Step {
	return ({ query, emojiDb, max, matches }) => {
		emojiDb.some(x => {
			if (isMatch(x, query)) matches.set(originalNameOf(x), { emoji: x, score: query.length + bonus });
			return matches.size === max;
		});
	};
}

function setScoreIfNull(bonus: number, isMatch: NameTest): Step {
	return context => setScore(bonus, (x, query) => isMatch(x, query) && !context.matches.has(originalNameOf(x)))(context);
}

function addFuzzyHits(): Step {
	return ({ query, emojiDb, matches }) => {
		if (query.length < FUZZY_MIN_QUERY_LENGTH) return;
		for (const hit of fuzzyHits(query, emojiDb, matches)) {
			matches.set(hit.emoji.name, hit);
		}
	};
}

const exactSteps: Step[] = [
	setScore(3, (x, q) => x.name === q && !isAlias(x)),
	setScoreIfNull(2, (x, q) => x.name === q),
];

const partialSteps: Step[] = [
	setScoreIfNull(1, (x, q) => x.name.startsWith(q) && !isAlias(x)),
	setScoreIfNull(0, (x, q) => x.name.startsWith(q)),
	setScoreIfNull(-1, (x, q) => x.name.includes(q)),
];

class EmojiScorer {
	static run(steps: Step[], query: string, emojiDb: EmojiDef[], max: number): Map<string, EmojiScore> {
		const context: SearchContext = { query, emojiDb, max, matches: new Map() };
		for (const [i, step] of steps.entries()) {
			const isFirstStep = i === 0;
			if (!isFirstStep && context.matches.size >= max) break;
			step(context);
		}
		return context.matches;
	}
}

function topByScore(matched: Map<string, EmojiScore>, max: number): EmojiDef[] {
	return [...matched.values()]
		.sort((x, y) => y.score - x.score)
		.slice(0, max)
		.map(it => it.emoji);
}

function countQueryCharsFoundInOrder(queryChars: string[], name: string): number {
	let pos = 0;
	let found = 0;
	for (const c of queryChars) {
		pos = name.indexOf(c, pos);
		if (pos <= -1) break;
		found++;
	}
	return found;
}

// 全ヒットを足すと雑多になるので、オートコンプリートのポップアップに収まる数だけ採用する
function fuzzyHits(query: string, emojiDb: EmojiDef[], matched: Map<string, EmojiScore>): EmojiScore[] {
	const queryChars = [...query];
	const minFound = Math.ceil(queryChars.length / 2);
	const hits = new Map<string, EmojiScore>();

	for (const x of emojiDb) {
		const found = countQueryCharsFoundInOrder(queryChars, x.name);
		const score = found - 2;
		const alreadyScored = matched.get(originalNameOf(x))?.score ?? 0;
		if (found > minFound && score > alreadyScored) {
			hits.set(originalNameOf(x), { emoji: x, score });
		}
	}

	return [...hits.values()]
		.sort((x, y) => y.score - x.score)
		.slice(0, AUTOCOMPLETE_POPUP_SIZE);
}

export function searchEmoji(query: string | null, emojiDb: EmojiDef[], max = 30): EmojiDef[] {
	if (!query) {
		return [];
	}

	const matches = EmojiScorer.run([...exactSteps, ...partialSteps, addFuzzyHits()], query, emojiDb, max);
	return topByScore(matches, max);
}

export function searchEmojiExact(query: string | null, emojiDb: EmojiDef[], max = 30): EmojiDef[] {
	if (!query) {
		return [];
	}

	return topByScore(EmojiScorer.run(exactSteps, query, emojiDb, max), max);
}
