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
type Prioritizer = (x: EmojiDef, query: string) => number | null;

const originalNameOf = (x: EmojiDef) => x.aliasOf ?? x.name;
const isAlias = (x: EmojiDef) => Boolean(x.aliasOf);
const OWN_NAME_EXACT_PRIORITY = 3;

class EmojiPrioritizer {
	constructor(private prioritizers: Prioritizer[] = []) {}

	addPriority(prioritizer: Prioritizer): EmojiPrioritizer {
		return new EmojiPrioritizer([...this.prioritizers, prioritizer]);
	}

	priorityOf(x: EmojiDef, query: string): number | null {
		const priorities = this.prioritizers.map(prioritizer => prioritizer(x, query)).filter(priority => priority !== null);
		return priorities.length > 0 ? query.length + Math.max(...priorities) : null;
	}
}

const exactPrioritizer = new EmojiPrioritizer()
	.addPriority((x, q) => {
		if (x.name === q) return isAlias(x) ? 2 : OWN_NAME_EXACT_PRIORITY;
		return null;
	});

const partialPrioritizer = exactPrioritizer
	.addPriority((x, q) => {
		if (x.name.startsWith(q)) return isAlias(x) ? 0 : 1;
		return null;
	})
	.addPriority((x, q) => {
		if (x.name.includes(q)) return -1;
		return null;
	});

function rankByNameMatch(prioritizer: EmojiPrioritizer, query: string, emojiDb: EmojiDef[]): Map<string, EmojiScore> {
	const bestPerEmoji = new Map<string, RankedEmoji>();
	emojiDb.forEach((emoji, dbIndex) => {
		const score = prioritizer.priorityOf(emoji, query);
		if (score === null) return;
		const best = bestPerEmoji.get(originalNameOf(emoji));
		const replacesSameNamedEmoji = score === query.length + OWN_NAME_EXACT_PRIORITY;
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

	const matched = rankByNameMatch(partialPrioritizer, query, emojiDb);

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

	return topByScore(rankByNameMatch(exactPrioritizer, query, emojiDb), max);
}
