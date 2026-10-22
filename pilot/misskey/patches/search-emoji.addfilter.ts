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

type RankedEmoji = EmojiScore & { dbIndex: number };
type NameFilter = { bonus: number; test: (x: EmojiDef, query: string) => boolean };

const originalNameOf = (x: EmojiDef) => x.aliasOf ?? x.name;
const isAlias = (x: EmojiDef) => Boolean(x.aliasOf);
const OWN_NAME_EXACT_BONUS = 3;

class NameFilterChain {
	constructor(private filters: NameFilter[] = []) {}

	addFilter(bonus: number, test: NameFilter['test']): NameFilterChain {
		return new NameFilterChain([...this.filters, { bonus, test }]);
	}

	scoreOf(x: EmojiDef, query: string): number | null {
		const hit = this.filters.find(f => f.test(x, query));
		return hit ? query.length + hit.bonus : null;
	}
}

const exactNameFilters = new NameFilterChain()
	.addFilter(OWN_NAME_EXACT_BONUS, (x, q) => x.name === q && !isAlias(x))
	.addFilter(2, (x, q) => x.name === q);

const partialNameFilters = exactNameFilters
	.addFilter(1, (x, q) => x.name.startsWith(q) && !isAlias(x))
	.addFilter(0, (x, q) => x.name.startsWith(q))
	.addFilter(-1, (x, q) => x.name.includes(q));

function rankByNameMatch(filters: NameFilterChain, query: string, emojiDb: EmojiDef[]): Map<string, EmojiScore> {
	const bestPerEmoji = new Map<string, RankedEmoji>();
	emojiDb.forEach((emoji, dbIndex) => {
		const score = filters.scoreOf(emoji, query);
		if (score === null) return;
		const best = bestPerEmoji.get(originalNameOf(emoji));
		const replacesSameNamedEmoji = score === query.length + OWN_NAME_EXACT_BONUS;
		if (!best || score > best.score || (score === best.score && replacesSameNamedEmoji)) {
			bestPerEmoji.set(originalNameOf(emoji), { emoji, score, dbIndex });
		}
	});

	const ranked = [...bestPerEmoji.entries()].sort(([, x], [, y]) => y.score - x.score || x.dbIndex - y.dbIndex);
	return new Map(ranked);
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

	const matched = rankByNameMatch(partialNameFilters, query, emojiDb);

	if (matched.size < max && query.length >= FUZZY_MIN_QUERY_LENGTH) {
		for (const it of fuzzyHits(query, emojiDb, matched)) {
			matched.set(it.emoji.name, it);
		}
	}

	return topByScore(matched, max);
}

export function searchEmojiExact(query: string | null, emojiDb: EmojiDef[], max = 30): EmojiDef[] {
	if (!query) {
		return [];
	}

	return topByScore(rankByNameMatch(exactNameFilters, query, emojiDb), max);
}
