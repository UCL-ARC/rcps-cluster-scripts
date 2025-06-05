# vim: set ft=bash :

function slurm_am_operator() {
    local adminLevel
    adminLevel="$(sacctmgr show user "$USER" --noheader --parsable2 format=adminlevel)"
    case "${adminLevel}" in
        Operator|Administrator)
            return 0 ;;
        *)
            return 1 ;;
    esac
}
