// Extract units (functions/methods) and per-file convention facts from a TS/Vue tree.
// usage: node extract.mjs <repo root> <out dir>
import ts from '/opt/node22/lib/node_modules/typescript/lib/typescript.js';
import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2], out = process.argv[3];
const SKIP = /(^|\/)(node_modules|built|test|test-federation|test-server|migration|\.storybook|@types)\//;
const SKIP_FILE = /\.(d|test|stories|stories\.impl|spec)\.ts$|\.stories\.vue$|\.test\.ts$/;

function walk(d, acc = []) {
	for (const e of fs.readdirSync(d, { withFileTypes: true })) {
		const p = path.join(d, e.name);
		const rel = path.relative(root, p);
		if (e.isDirectory()) { if (!SKIP.test(rel + '/') && e.name !== '.git') walk(p, acc); }
		else if (/\.(ts|vue)$/.test(e.name) && !SKIP_FILE.test(e.name) && !SKIP.test(rel)) acc.push(rel);
	}
	return acc;
}

// layer = what role the file plays, from its path only
function layer(rel) {
	const r = rel;
	let m;
	if (r.startsWith('packages/backend/src/')) {
		const s = r.slice('packages/backend/src/'.length);
		if (s.startsWith('server/api/endpoints/')) return 'be:endpoint';
		if (s.startsWith('server/api/stream/')) return 'be:stream';
		if (s.startsWith('server/')) return 'be:server';
		if (s.startsWith('core/activitypub/')) return 'be:activitypub';
		if (s.startsWith('core/entities/')) return 'be:entity-pack';
		if (s.startsWith('core/')) return 'be:service';
		if (s.startsWith('queue/processors/')) return 'be:queue-processor';
		if (s.startsWith('queue/')) return 'be:queue';
		if (s.startsWith('models/')) return 'be:model';
		if (s.startsWith('misc/')) return 'be:misc';
		return 'be:other';
	}
	if (r.startsWith('packages/frontend/src/')) {
		const s = r.slice('packages/frontend/src/'.length);
		if (r.endsWith('.vue')) {
			if (s.startsWith('pages/')) return 'fe:page';
			if (s.startsWith('components/')) return 'fe:component';
			if (s.startsWith('ui/')) return 'fe:ui-shell';
			if (s.startsWith('widgets/')) return 'fe:widget';
			return 'fe:vue-other';
		}
		if (s.startsWith('utility/') || s.startsWith('lib/')) return 'fe:util';
		if (s.startsWith('composables/')) return 'fe:composable';
		if (s.startsWith('preferences')) return 'fe:preferences';
		if (s.startsWith('pages/')) return 'fe:page-ts';
		return 'fe:module';
	}
	if (r.startsWith('packages/frontend-embed/')) return 'fe-embed';
	if (r.startsWith('packages/misskey-js/')) return 'misskey-js';
	if (r.startsWith('packages/sw/')) return 'sw';
	if ((m = r.match(/^packages\/([^/]+)\//))) return 'pkg:' + m[1];
	return 'other';
}

const READ = /^(find|findBy|findOne|findOneBy|findOneByOrFail|findOneOrFail|findAndCount|findBy|count|countBy|exist|exists|existsBy|createQueryBuilder|query|sum|average|maximum|minimum)$/;
const WRITE = /^(insert|update|delete|save|upsert|increment|decrement|remove|softDelete|restore|clear|insertOne|updateOne)$/;
const REDIS_RD = /^(get|mget|hget|hgetall|hmget|lrange|zrange|zrevrange|zrangebyscore|zrevrangebyscore|zscore|smembers|sismember|llen|zcard|exists|keys|scan|ttl|pttl|xrange|xrevrange|hlen|zcount|lindex|scard|srandmember|dbsize|type)$/;
const REDIS_WR = /^(set|setex|psetex|mset|del|hset|hmset|hdel|lpush|rpush|lpop|rpop|ltrim|zadd|zrem|zremrangebyscore|zremrangebyrank|sadd|srem|incr|incrby|decr|decrby|hincrby|expire|pexpire|publish|xadd|xtrim|rename|unlink|flushdb|eval|setnx|zincrby|lrem|lset)$/;
const REDISRX = /^(redis|redisClient|redisForPub|redisForSub|redisForTimelines|redisForReactions|redisForRemoteApis|redisForRemoteApi|pipeline)$/;

// classify one call expression; returns a leaf tag or null
function leafOf(callee) {
	const parts = callee.replace(/^this\./, '').replace(/\?\./g, '.').split('.');
	const last = parts[parts.length - 1];
	const recv = parts.slice(0, -1).join('.');
	const r0 = parts[0];
	if (parts.length > 1 && /(Repository|Repo)$/.test(parts[0]) || /^db\b/.test(recv) && parts.length > 1 && /^(query|manager|transaction|createQueryBuilder)$/.test(last)) {
		if (READ.test(last)) return 'db.read';
		if (WRITE.test(last)) return 'db.write';
		if (last === 'transaction') return 'db.write';
	}
	if (REDISRX.test(r0) && parts.length > 1) return REDIS_WR.test(last) ? 'redis.write' : (REDIS_RD.test(last) ? 'redis.read' : 'redis.other');
	if (/^(qb|query|q|builder|subQuery)$/.test(r0) && /^(where|andWhere|orWhere|getMany|getOne|getRawMany|getRawOne|getCount|getManyAndCount|select|addSelect|from|innerJoin|leftJoin|innerJoinAndSelect|leftJoinAndSelect|orderBy|addOrderBy|limit|offset|setParameters|setParameter|take|skip|andWhere|execute)$/.test(last)) return 'db.read';
	if (/^(redisPipeline)$/.test(r0) || /^redisClient\.pipeline$/.test(callee.replace(/^this\./, ''))) return 'redis.write';
	if (/^moderationLogService$/.test(r0)) return 'audit.log';
	if (/^(dbQueue|queue|[a-zA-Z]*Queue)$/.test(r0) && /^(add|addBulk)$/.test(last)) return 'queue.enqueue';
	if (/^(globalEventService)$/.test(r0) && /^publish/.test(last)) return 'event.publish';
	if (/^(queueService)$/.test(r0)) return 'queue.enqueue';
	if (/^(httpRequestService|apRequestService|downloadService)$/.test(r0)) return 'net.http';
	if (/^(apResolverService|apDbResolverService|apRendererService|apPersonService|apNoteService|apImageService|apMentionService|apAudienceService|apQuestionService|apInboxService|apDeliverManagerService|apLoggerService|apUtilityService)$/.test(r0)) return 'federation.ap';
	if (/^(userEntityService|noteEntityService|driveFileEntityService|[a-zA-Z]+EntityService)$/.test(r0)) return 'pack.entity';
	if (/^(emit|globalEvents\.emit)$/.test(callee)) return 'vue.emit';
	if (/^[a-z][A-Za-z]*Service$/.test(r0) && parts.length > 1 && !/^(idService|loggerService)$/.test(r0) && !/^(userEntityService|noteEntityService)$/.test(r0)) return 'service.call';
	if (/^(fetch|got)$/.test(callee)) return 'net.http';
	if (/^(fs|fsp|fsPromises)\./.test(callee) || /^(createReadStream|createWriteStream)$/.test(callee)) return 'fs';
	if (/^(misskeyApi|misskeyApiGet|os\.apiWithDialog|os\.api|apiWithDialog|apiGet)$/.test(callee)) return 'api.call';
	if (/^os\.(alert|confirm|popup|popupMenu|contextMenu|popupAsyncWithDialog|inputText|inputNumber|select|waiting|toast|success)/.test(callee)) return 'ui.dialog';
	if (/^(ref|shallowRef|computed|reactive|watch|watchEffect|onMounted|onUnmounted|provide|inject|useTemplateRef|toRef|toRefs|nextTick|customRef|defineModel)$/.test(callee)) return 'vue.state';
	if (/^(router|useRouter|mainRouter)\./.test(callee) || callee === 'useRouter') return 'nav';
	if (/^(i18n)\./.test(callee)) return 'i18n';
	if (/^(store|prefer|miLocalStorage|localStorage|sessionStorage|\$i|ensureSignin|miLocalStorage)\b/.test(callee)) return 'local.state';
	if (/^(document|window|navigator|location)\./.test(callee) || /^(addEventListener|removeEventListener|requestAnimationFrame|setTimeout|setInterval)$/.test(callee)) return 'dom';
	if (/^(useStream|stream|connection)\b/.test(callee)) return 'stream';
	if (/^(this\.)?logger\.|^logger\./.test(callee) || /^(console)\./.test(callee)) return 'log';
	if (/^(bcrypt|crypto|argon2|secureRndstr|genId|idService)\b/.test(callee)) return 'crypto.id';
	return null;
}

const CHAIN = new Set(['map', 'filter', 'reduce', 'flatMap', 'some', 'every', 'find', 'findIndex', 'forEach', 'sort', 'flat']);
const WORD = /[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+/g;
const words = (s) => (s.match(WORD) || []).map((w) => w.toLowerCase());

function analyzeUnit(sf, node, name, cls, kind, rel) {
	const body = node.body ?? node;
	const f = {
		loops: 0, chain: 0, mutate: 0, lets: 0, consts: 0, awaits: 0, thens: 0, throws: 0, tries: 0, sw: 0, tern: 0, ifs: 0, opt: 0, thisUse: 0,
		maxDepth: 0, cyc: 1, calls: 0, retBool: 0, returns: 0, nonNull: 0, anyCast: 0,
	};
	const leaves = {}; const callees = [];
	const ids = new Set();
	function visit(n, depth) {
		f.maxDepth = Math.max(f.maxDepth, depth);
		switch (n.kind) {
			case ts.SyntaxKind.ForStatement: case ts.SyntaxKind.ForInStatement: case ts.SyntaxKind.ForOfStatement: case ts.SyntaxKind.WhileStatement: case ts.SyntaxKind.DoStatement:
				f.loops++; f.cyc++; break;
			case ts.SyntaxKind.IfStatement: f.ifs++; f.cyc++; break;
			case ts.SyntaxKind.CaseClause: case ts.SyntaxKind.CatchClause: case ts.SyntaxKind.ConditionalExpression: f.cyc++; if (n.kind === ts.SyntaxKind.ConditionalExpression) f.tern++; break;
			case ts.SyntaxKind.BinaryExpression: {
				const k = n.operatorToken.kind;
				if (k === ts.SyntaxKind.AmpersandAmpersandToken || k === ts.SyntaxKind.BarBarToken || k === ts.SyntaxKind.QuestionQuestionToken) f.cyc++;
				if (k >= ts.SyntaxKind.FirstAssignment && k <= ts.SyntaxKind.LastAssignment && (n.left.kind === ts.SyntaxKind.PropertyAccessExpression || n.left.kind === ts.SyntaxKind.ElementAccessExpression)) f.mutate++;
				break;
			}
			case ts.SyntaxKind.VariableDeclarationList: if (n.flags & ts.NodeFlags.Let) f.lets += n.declarations.length; else f.consts += n.declarations.length; break;
			case ts.SyntaxKind.AwaitExpression: f.awaits++; break;
			case ts.SyntaxKind.ThrowStatement: f.throws++; break;
			case ts.SyntaxKind.TryStatement: f.tries++; break;
			case ts.SyntaxKind.SwitchStatement: f.sw++; break;
			case ts.SyntaxKind.QuestionDotToken: f.opt++; break;
			case ts.SyntaxKind.NonNullExpression: f.nonNull++; break;
			case ts.SyntaxKind.AsExpression: if (n.type.kind === ts.SyntaxKind.AnyKeyword) f.anyCast++; break;
			case ts.SyntaxKind.ThisKeyword: f.thisUse++; break;
			case ts.SyntaxKind.ReturnStatement: f.returns++; break;
			case ts.SyntaxKind.Identifier: if (n.text.length > 2) ids.add(n.text); break;
			case ts.SyntaxKind.CallExpression: {
				f.calls++;
				const callee = n.expression.getText(sf).replace(/\s+/g, '').replace(/\(.*$/s, '');
				if (callee.length < 120) {
					callees.push(callee);
					const m = callee.split('.').pop();
					if (callee.includes('.') && CHAIN.has(m)) f.chain++;
					if (m === 'then' || m === 'catch') f.thens++;
					const l = leafOf(callee);
					if (l) leaves[l] = (leaves[l] || 0) + 1;
				}
				break;
			}
		}
		const nested = depth + ((ts.isBlock(n) || ts.isArrowFunction(n) || ts.isFunctionExpression(n)) ? 1 : 0);
		ts.forEachChild(n, (c) => visit(c, nested));
	}
	visit(body, 0);
	const start = node.getStart(sf), end = node.getEnd();
	const lc = sf.getLineAndCharacterOfPosition(start).line, le = sf.getLineAndCharacterOfPosition(end).line;
	const ranges = ts.getLeadingCommentRanges(sf.text, node.pos) || [];
	const doc = ranges.map((r) => sf.text.slice(r.pos, r.end)).filter((t) => !/^\/\/\s*(eslint|@ts-|prettier)/.test(t)).join('\n');
	const decos = (ts.canHaveDecorators(node) ? ts.getDecorators(node) || [] : []).map((d) => d.expression.getText(sf).replace(/\(.*$/s, ''));
	const rt = node.type ? node.type.getText(sf) : '';
	return {
		file: rel, name, cls, kind, layer: layer(rel), line: lc + 1, loc: le - lc + 1,
		async: !!(node.modifiers && node.modifiers.some((m) => m.kind === ts.SyntaxKind.AsyncKeyword)) || (f.awaits > 0),
		nparams: (node.parameters || []).length, rtype: rt.slice(0, 60), decos, docLen: doc.length, hasDoc: doc.length > 0,
		isPrivate: !!(node.modifiers && node.modifiers.some((m) => m.kind === ts.SyntaxKind.PrivateKeyword || m.kind === ts.SyntaxKind.ProtectedKeyword)) || (node.name && node.name.kind === ts.SyntaxKind.PrivateIdentifier),
		isExported: !!(node.modifiers && node.modifiers.some((m) => m.kind === ts.SyntaxKind.ExportKeyword)),
		...f, leaves, callees: callees.slice(0, 60), nids: ids.size,
	};
}

function processSource(text, rel, scriptKind, units, fileFacts) {
	const sf = ts.createSourceFile(rel, text, ts.ScriptTarget.Latest, true, scriptKind);
	function isFn(n) { return ts.isFunctionDeclaration(n) || ts.isMethodDeclaration(n) || ts.isArrowFunction(n) || ts.isFunctionExpression(n) || ts.isGetAccessor(n) || ts.isSetAccessor(n); }
	function nameOf(n, parent) {
		if (n.name) return n.name.getText(sf);
		if (parent && ts.isVariableDeclaration(parent)) return parent.name.getText(sf);
		if (parent && ts.isPropertyAssignment(parent)) return parent.name.getText(sf);
		if (parent && ts.isPropertyDeclaration(parent)) return parent.name.getText(sf);
		if (parent && ts.isCallExpression(parent) && parent.expression.kind === ts.SyntaxKind.SuperKeyword) return '<handler>';
		return null;
	}
	function go(n, parent, cls, inUnit) {
		let c = cls;
		if (ts.isClassDeclaration(n) || ts.isClassExpression(n)) {
			c = n.name ? n.name.text : '<anon>';
			const ext = (n.heritageClauses || []).flatMap((h) => h.types.map((t) => t.getText(sf).slice(0, 50)));
			const decos = (ts.getDecorators(n) || []).map((d) => d.expression.getText(sf).replace(/\(.*$/s, ''));
			const members = n.members;
			fileFacts.classes.push({ name: c, ext, decos, nMethods: members.filter(ts.isMethodDeclaration).length, nProps: members.filter(ts.isPropertyDeclaration).length, ctorParams: (members.find(ts.isConstructorDeclaration)?.parameters || []).map((p) => ({ deco: (ts.getDecorators(p) || []).map((d) => d.expression.getText(sf).slice(0, 40)), mods: (p.modifiers || []).filter((m) => m.kind !== ts.SyntaxKind.Decorator).map((m) => ts.SyntaxKind[m.kind]), type: p.type ? p.type.getText(sf).slice(0, 40) : '' })) });
		}
		if (!inUnit && isFn(n) && n.body) {
			const nm = nameOf(n, parent);
			const topLevelArrow = (ts.isArrowFunction(n) || ts.isFunctionExpression(n));
			const named = nm && (!topLevelArrow || (parent && (ts.isVariableDeclaration(parent) || ts.isPropertyAssignment(parent) || ts.isPropertyDeclaration(parent) || ts.isCallExpression(parent) && parent.expression.kind === ts.SyntaxKind.SuperKeyword)));
			if (named) { units.push(analyzeUnit(sf, n, nm, c, ts.SyntaxKind[n.kind].replace('Declaration', ''), rel)); return; }
		}
		ts.forEachChild(n, (ch) => go(ch, n, c, inUnit));
	}
	go(sf, null, null, false);
	// file-level facts
	fileFacts.imports = [];
	sf.forEachChild((n) => { if (ts.isImportDeclaration(n)) fileFacts.imports.push(n.moduleSpecifier.getText(sf).replace(/['"]/g, '')); });
	fileFacts.defaultExport = /export\s+default/.test(text);
	fileFacts.namedExports = (text.match(/^export\s+(const|function|class|type|interface|async function)/gm) || []).length;
	fileFacts.hasBindThis = /@bindThis/.test(text);
	fileFacts.injectable = /@Injectable\(/.test(text);
	fileFacts.diInject = (text.match(/@Inject\(DI\./g) || []).length;
	fileFacts.endpoint = /extends\s+Endpoint</.test(text);
	fileFacts.anyKw = (text.match(/:\s*any\b|\bas any\b/g) || []).length;
	fileFacts.tsIgnore = (text.match(/@ts-(ignore|expect-error|nocheck)/g) || []).length;
	fileFacts.eslintDisable = (text.match(/eslint-disable/g) || []).length;
	fileFacts.nonNull = (text.match(/[A-Za-z0-9_\)\]]!\.|[A-Za-z0-9_\)\]]!;/g) || []).length;
	fileFacts.fnArrowTop = (text.match(/^export const \w+\s*=\s*(async\s*)?\(/gm) || []).length;
	fileFacts.fnDeclTop = (text.match(/^export (async )?function /gm) || []).length;
}

const files = walk(root).filter((r) => /^packages\/(backend\/src|frontend\/src|frontend-embed\/src|misskey-js\/src|sw\/src|frontend-shared)/.test(r));
const unitsOut = fs.createWriteStream(path.join(out, 'units.jsonl'));
const filesOut = fs.createWriteStream(path.join(out, 'files.jsonl'));
let nf = 0, nu = 0;
for (const rel of files) {
	const text = fs.readFileSync(path.join(root, rel), 'utf8');
	const ff = { file: rel, layer: layer(rel), loc: text.split('\n').length, classes: [], spdx: /SPDX-License-Identifier/.test(text.slice(0, 400)) };
	const units = [];
	try {
		if (rel.endsWith('.vue')) {
			const sm = [...text.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)];
			const tpl = (text.match(/<template[^>]*>([\s\S]*)<\/template>/) || [])[1] || '';
			const sty = [...text.matchAll(/<style([^>]*)>/g)].map((m) => m[1]);
			ff.vue = {
				scriptSetup: sm.some((m) => /\bsetup\b/.test(m[1])), langTs: sm.some((m) => /lang="ts"/.test(m[1])),
				optionsApi: /export default\s*(defineComponent\()?\s*\{/.test(text) && !sm.some((m) => /\bsetup\b/.test(m[1])),
				defineProps: /defineProps</.test(text) ? 'type' : (/defineProps\(/.test(text) ? 'runtime' : 'none'),
				withDefaults: /withDefaults\(/.test(text), defineEmits: /defineEmits</.test(text) ? 'type' : (/defineEmits\(/.test(text) ? 'runtime' : 'none'),
				defineModel: /defineModel/.test(text), tplLoc: tpl.split('\n').length, scriptLoc: sm.reduce((a, m) => a + m[2].split('\n').length, 0),
				styleModule: sty.some((s) => /module/.test(s)), styleScoped: sty.some((s) => /scoped/.test(s)), styleLangScss: sty.some((s) => /scss/.test(s)), nStyle: sty.length,
				i18nUse: (tpl.match(/i18n\.(ts|tsx)\./g) || []).length + (text.match(/i18n\.(ts|tsx)\./g) || []).length,
				rawTextNodes: (tpl.match(/>\s*[A-Za-z぀-ヿ一-鿿][^<>{}\n]{3,}\s*</g) || []).length,
				nativeAlert: /(^|[^.\w])(alert|confirm|prompt)\(/.test(sm.map((m) => m[2]).join('\n')),
				vFor: (tpl.match(/v-for=/g) || []).length, vIf: (tpl.match(/v-if=/g) || []).length, vModel: (tpl.match(/v-model/g) || []).length,
				mkComp: (tpl.match(/<Mk[A-Z]\w*/g) || []).length, nTplElems: (tpl.match(/<[A-Za-z]/g) || []).length,
				classNameStyle: (tpl.match(/:class="\$style\./g) || []).length + (tpl.match(/class="\$style\./g) || []).length,
				classLiteral: (tpl.match(/\sclass="[^"$]*"/g) || []).length,
			};
			for (const m of sm) processSource(m[2], rel, ts.ScriptKind.TS, units, ff);
		} else {
			processSource(text, rel, ts.ScriptKind.TS, units, ff);
		}
	} catch (e) { ff.err = String(e).slice(0, 100); }
	for (const u of units) { unitsOut.write(JSON.stringify(u) + '\n'); nu++; }
	filesOut.write(JSON.stringify(ff) + '\n'); nf++;
}
unitsOut.end(); filesOut.end();
console.error(`files=${nf} units=${nu}`);
