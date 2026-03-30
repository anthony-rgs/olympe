import subprocess

print("🚀 Run billion club script...\n")

try:
  # 1) Run scraper from Artemis
  result = subprocess.run(
    ["bash", "-lc", "PYTHONPATH=/code-artemis python3 -u -m src.billionClubScripts.billion_club"],
    check=True
  )
  print("✅ All datas scraped !\n")


  # 2) If OK, run ingest into Athena from Owl
  print("🚀 Run insert in to Athena script...\n")
  subprocess.run(
    ["docker", "exec", "olympe-owl", "python", "-u", "-m", "app.cli", "all"],

    check=True,
  )
  print("✅ Datas inserted in Athena !\n")

except subprocess.CalledProcessError as e:
  print("❌ Error during script execution")
  print("Exit code :", e.returncode)

# Kill chromium process
finally:
  subprocess.run(['pkill', '-f', 'chromium'], capture_output=True)
  print('🧹 Chromium processes cleaned up')