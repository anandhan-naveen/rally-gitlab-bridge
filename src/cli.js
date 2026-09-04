import { Command } from 'commander';
import { preview, importScope, syncScope, status } from './service.js';

const program = new Command();
program.name('rally-gitlab-bridge').description('Selective Rally ↔ GitLab bridge').version('0.3.0');

program.command('preview').argument('<scopeType>').argument('[scopeValue]', '').action((scopeType, scopeValue) => {
  console.log(JSON.stringify(preview(scopeType, scopeValue), null, 2));
});
program.command('import').argument('<scopeType>').argument('[scopeValue]', '').option('--dry-run').action(async (scopeType, scopeValue, opts) => {
  console.log(JSON.stringify(await importScope(scopeType, scopeValue, { dryRun: opts.dryRun }), null, 2));
});
program.command('sync').argument('<scopeType>').argument('[scopeValue]', '').option('--dry-run').action(async (scopeType, scopeValue, opts) => {
  console.log(JSON.stringify(await syncScope(scopeType, scopeValue, { dryRun: opts.dryRun }), null, 2));
});
program.command('status').action(() => console.log(JSON.stringify(status(), null, 2)));

program.parseAsync().catch(err => { console.error(err.message); process.exitCode = 1; });
