# Contributing

Keep process matching narrow and backed by tests. Any new termination path must
prove PID-incarnation safety, revalidate the parent immediately before the
mutation and avoid blanket process-tree kills.

Run before submitting a change:

```powershell
python -m unittest -v test_zombie_killer
start-zombie-killer-admin.bat --check
```
