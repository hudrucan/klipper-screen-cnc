#!/bin/bash

set -e

SCRIPTPATH=$(dirname -- "$(readlink -f -- "$0")")
KSPATH=$(dirname "$SCRIPTPATH")
KSENV="${KLIPPERSCREEN_VENV:-${HOME}/.klipper-screen-env}"
KLIPPER_PATH="${KLIPPER_PATH:-${HOME}/klipper}"
KLIPPER_EXTRAS_PATH="${KLIPPER_EXTRAS_PATH:-}"
INSTALL_KLIPPER_EXTRAS="${INSTALL_KLIPPER_EXTRAS:-1}"

SERVICE="${KLIPPERSCREEN_SERVICE:-klipper-screen.service}"

echo "Updating Klipper Screen CNC dependencies"
echo "Update user: $(id -un 2>/dev/null || true)"
echo "HOME: ${HOME}"
echo "Repo path: ${KSPATH}"

restart_systemd_service()
{
    local service_name="$1"
    if ! command -v systemctl >/dev/null 2>&1; then
        return
    fi

    if [ -t 0 ]; then
        sudo systemctl restart "$service_name"
    else
        sudo -n systemctl restart "$service_name" || \
            echo "Skipping ${service_name} restart; Moonraker should restart managed services"
    fi
}

if [ ! -d "$KSENV" ]; then
    echo "Virtual environment not found at ${KSENV}; creating it"
    python3 -m venv "$KSENV"
fi

. "${KSENV}/bin/activate"

if [[ "$(uname -m)" =~ armv[67]l ]]; then
    pip --disable-pip-version-check install \
        --extra-index-url https://www.piwheels.org/simple \
        -r "${KSPATH}/scripts/KlipperScreen-requirements.txt" \
        --prefer-binary
else
    pip --disable-pip-version-check install \
        -r "${KSPATH}/scripts/KlipperScreen-requirements.txt" \
        --prefer-binary
fi

deactivate

install_klipper_extras()
{
    if [ "$INSTALL_KLIPPER_EXTRAS" = "0" ]; then
        echo "Skipping Klipper CNC extras install"
        return
    fi

    local extras_src="${KSPATH}/klipper-extras"
    local extras_dst=""
    if [ ! -d "$extras_src" ]; then
        echo "Klipper CNC extras source not found at ${extras_src}"
        return
    fi

    if [ -n "$KLIPPER_EXTRAS_PATH" ]; then
        extras_dst="$KLIPPER_EXTRAS_PATH"
    elif [ -d "${KLIPPER_PATH}/klippy/extras" ]; then
        extras_dst="${KLIPPER_PATH}/klippy/extras"
    else
        local candidate
        for candidate in \
            "${HOME}/klipper/klippy/extras" \
            "${HOME}/Klipper/klippy/extras" \
            "${HOME}/printer_data/klipper/klippy/extras" \
            /home/*/klipper/klippy/extras \
            /home/*/Klipper/klippy/extras
        do
            if [ -d "$candidate" ]; then
                extras_dst="$candidate"
                break
            fi
        done
    fi

    if [ -z "$extras_dst" ] || [ ! -d "$extras_dst" ]; then
        echo "Klipper CNC extras were not installed: could not find klippy/extras"
        echo "Set KLIPPER_PATH=/path/to/klipper or KLIPPER_EXTRAS_PATH=/path/to/klippy/extras"
        echo "Tried:"
        echo "  ${KLIPPER_PATH}/klippy/extras"
        echo "  ${HOME}/klipper/klippy/extras"
        echo "  ${HOME}/Klipper/klippy/extras"
        echo "  ${HOME}/printer_data/klipper/klippy/extras"
        return
    fi

    echo "Installing Klipper CNC extras to ${extras_dst}"
    local extra_file
    local installed=0
    for extra_file in "${extras_src}"/*.py; do
        if [ ! -f "$extra_file" ]; then
            continue
        fi
        install_extra_file "$extra_file" "${extras_dst}"
        installed=$((installed + 1))
    done

    if [ "$installed" -eq 0 ]; then
        echo "No Klipper CNC extras found in ${extras_src}"
        return 1
    fi

    restart_systemd_service klipper || true
}

install_extra_file()
{
    local src="$1"
    local extras_dst="$2"
    local filename
    filename=$(basename "$src")
    local dst="${extras_dst}/${filename}"

    if [ ! -f "$src" ]; then
        echo "Missing Klipper CNC extra source: ${src}"
        return 1
    fi

    cp -f "$src" "$dst"

    if cmp -s "$src" "$dst"; then
        echo "Installed ${filename} -> ${dst}"
    else
        echo "Failed to verify copied extra: ${filename}"
        return 1
    fi
}

install_klipper_extras

if command -v systemctl >/dev/null 2>&1; then
    if [ -t 0 ]; then
        sudo systemctl daemon-reload
    else
        sudo -n systemctl daemon-reload || true
    fi
    restart_systemd_service "$SERVICE"
fi

echo "Klipper Screen CNC update complete"
