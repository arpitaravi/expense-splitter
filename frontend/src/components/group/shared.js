export function invalidateGroup(qc, gid) {
  ["group", "expenses", "balances", "settlements", "insights", "activity", "recurring"].forEach((k) =>
    qc.invalidateQueries({ queryKey: [k, String(gid)] }));
  qc.invalidateQueries({ queryKey: ["summary"] });
  qc.invalidateQueries({ queryKey: ["groups"] });
}
