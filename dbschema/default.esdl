module default {
    type Playbook {
        required property name -> str;
    }

    type Run {
        required link playbook -> Playbook;
    }

    type Error {
        required link run -> Run;
        link issue -> Issue;
    }

    type Issue {
        link parent -> Issue;
        multi link refs -> Issue {
            property reason -> str;
        }
    }
}
